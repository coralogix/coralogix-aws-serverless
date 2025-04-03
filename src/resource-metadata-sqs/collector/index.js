/**
 * AWS Resource Tags Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 */

"use strict";

import assert from 'assert';
import { collectLambdaResources } from './lambda.js';
import { collectEc2Resources } from './ec2.js';
import { sendToSqs } from './sqs.js';
import { STSClient, AssumeRoleCommand, GetCallerIdentityCommand } from "@aws-sdk/client-sts";

const validateAndExtractConfiguration = () => {
    const excludeEC2 = String(process.env.IS_EC2_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true";
    const excludeLambda = String(process.env.IS_LAMBDA_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true";
    const regions = process.env.REGIONS?.split(',') || [process.env.AWS_REGION];
    const roleArns = process.env.CROSSACCOUNT_IAM_ROLE_ARNS ? process.env.CROSSACCOUNT_IAM_ROLE_ARNS.split(',') : [];

    return { excludeEC2, excludeLambda, regions, roleArns };
};
const { excludeEC2, excludeLambda, regions, roleArns } = validateAndExtractConfiguration();

// Function to assume a role using AWS SDK v3
const assumeRole = async (roleArn) => {
    const stsClient = new STSClient({});
    const command = new AssumeRoleCommand({
        RoleArn: roleArn,
        RoleSessionName: 'CrossAccountLambdaSession'
    });
    const data = await stsClient.send(command);
    return {
        accessKeyId: data.Credentials.AccessKeyId,
        secretAccessKey: data.Credentials.SecretAccessKey,
        sessionToken: data.Credentials.SessionToken
    };
};

// Function to get the current account ID
const getAccountId = async (clientConfig = {}) => {
    const stsClient = new STSClient(clientConfig);
    const command = new GetCallerIdentityCommand({});
    const data = await stsClient.send(command);
    return data.Account;
};

/**
 * @description Lambda function handler
 */
export const handler = async (_, context) => {
    console.info(`Starting a one-time collection of resources`);

    let collectionPromises = [];

    // Collect resources from the current account
    const currentAccountId = await getAccountId();
    for (const region of regions) {
        if (!excludeEC2) {
            let ec2 = collectEc2ResourceBatches(region, currentAccountId);
            collectionPromises.push(ec2);
        }

        if (!excludeLambda) {
            let lambda = collectLambdaResourceBatches(region, currentAccountId);
            collectionPromises.push(lambda);
        }
    }

    // Collect resources from other accounts if role ARNs are provided
    for (const roleArn of roleArns) {
        const credentials = await assumeRole(roleArn);
        const clientConfig = { credentials };
        const accountId = await getAccountId(clientConfig);

        for (const region of regions) {
            if (!excludeEC2) {
                let ec2 = collectEc2ResourceBatches(region, accountId, clientConfig);
                collectionPromises.push(ec2);
            }

            if (!excludeLambda) {
                let lambda = collectLambdaResourceBatches(region, accountId, clientConfig);
                collectionPromises.push(lambda);
            }
        }
    }

    // Wait for all resources to be collected
    // Otherwise, if sent immediately, there may be an API rate limit exceeded error
    // As the generator will start queueing the Lambda API before the collector is done
    const collectedResources = await Promise.all(collectionPromises);

    for (const { source, region, account, batches } of collectedResources) {
        for (const batch of batches) {
            console.info(`Sending ${source} resources batch from account ${account} region ${region} to SQS`);
            await sendToSqs({ source, region, account, resources: batch });
            console.info(`Sent ${source} resources batch from account ${account} region ${region} to SQS`);
        }
    }

    console.info("Collection done");
};

const collectLambdaResourceBatches = async (region, accountId, clientConfig = {}) => {
    console.info(`Collecting Lambda resources in ${region} from account ${accountId}`);
    const batches = [];
    for await (const batch of collectLambdaResources(region, clientConfig)) {
        batches.push(batch);
    }
    return { source: "collector.lambda", region: region, account: accountId, batches };
};

const collectEc2ResourceBatches = async (region, accountId, clientConfig = {}) => {
    console.info(`Collecting EC2 resources in ${region} from account ${accountId}`);
    const batches = [];
    for await (const batch of collectEc2Resources(region, clientConfig)) {
        batches.push(batch);
    }
    return { source: "collector.ec2", region: region, account: accountId, batches };
};
