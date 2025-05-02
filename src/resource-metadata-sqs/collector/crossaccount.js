/**
 * Cross-Account functionality for AWS Resource Collection
 * 
 * @file        Cross-account collection methods for Lambda function
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 */

"use strict";

import { STSClient, AssumeRoleCommand, GetCallerIdentityCommand } from "@aws-sdk/client-sts";
import { ConfigServiceClient, SelectAggregateResourceConfigCommand } from "@aws-sdk/client-config-service";
import { collectLambdaResources } from './lambda.js';
import { collectEc2Resources } from './ec2.js';

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
export const getAccountId = async (clientConfig = {}) => {
    const stsClient = new STSClient(clientConfig);
    const command = new GetCallerIdentityCommand({});
    const data = await stsClient.send(command);
    return data.Account;
};

// Function to collect Lambda resources using AWS Config
export const collectResourcesViaConfig = async (configAggregatorName, resourceType) => {
    console.info("Collecting Lambda resources via AWS Config");
    try {
        const configClient = new ConfigServiceClient({ region: process.env.AWS_REGION });
        const batchSize = 50;

        const baseQuery = `SELECT arn, resourceId, awsRegion, accountId WHERE resourceType = '${resourceType}'`;

        let nextToken;
        let allBatches = [];
        let resources = [];
        let totalResources = 0;

        // Paginate through all results
        do {
            // Create a new command with the updated token for each request
            const command = new SelectAggregateResourceConfigCommand({
                Expression: baseQuery,
                ConfigurationAggregatorName: configAggregatorName,
                Limit: batchSize,
                NextToken: nextToken
            });

            const response = await configClient.send(command);
            nextToken = response.NextToken;

            // Process results
            if (response.Results && response.Results.length > 0) {

                for (const resultString of response.Results) {
                    const result = JSON.parse(resultString);

                    // Format function data to match the expected structure
                    resources.push({
                        ResourceArn: result.arn,
                        ResourceId: result.resourceId,
                        Region: result.awsRegion,
                        Account: result.accountId
                    });
                    totalResources += 1;
                }
            }
        } while (nextToken);

        // Group resources by region and account
        const groupedResources = resources.reduce((acc, resource) => {
            const key = `${resource.Region}:${resource.Account}`;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(resource);
            return acc;
        }, {});

        // Create batches for each region-account pair with cleaned-up resources
        for (const [key, resources] of Object.entries(groupedResources)) {
            const [region, account] = key.split(':');

            // Clean up each resource by removing redundant Region and Account properties
            const processedResources = resources.map(resource => {
                // Create a new object without Region and Account
                const { Region, Account, ...processedResource } = resource;
                return processedResource;
            });

            // Split into smaller batches based on batchSize
            const resourceBatches = [];
            for (let i = 0; i < processedResources.length; i += batchSize) {
                const batch = processedResources.slice(i, i + batchSize);
                resourceBatches.push(batch);
            }

            const resourceTypeKey = resourceType.split('::')[1].toLowerCase();
            allBatches.push({
                source: `collector.${resourceTypeKey}.config`,
                region,
                account,
                batches: resourceBatches // Now an array of smaller batches
            });
        }

        console.info(`Collected ${totalResources} ${resourceType} cross-account resources via AWS Config`);
        return allBatches;
    } catch (error) {
        console.error(`Error collecting ${resourceType} cross-account resources via AWS Config:`, error);
        return null;
    }
};

// Helper function to collect via Static IAM roles
export const collectViaStaticIAM = async (roleArns, regions, resourceType) => {
    const resourceTypeKey = resourceType.split('::')[1].toLowerCase();
    let allBatches = [];
    for (const roleArn of roleArns) {
        try {
            const credentials = await assumeRole(roleArn);
            const clientConfig = { credentials };
            const accountId = await getAccountId(clientConfig);

            for (const region of regions) {
                const batches = [];

                switch (resourceType) {
                    case 'AWS::Lambda::Function':
                        for await (const batch of collectLambdaResources(region, clientConfig)) {
                            batches.push(batch);
                        }
                        break;
                    case 'AWS::EC2::Instance':
                        for await (const batch of collectEc2Resources(region, clientConfig)) {
                            batches.push(batch);
                        }
                        break;
                    default:
                        throw new Error(`Unsupported resource type: ${resourceType}`);
                }
                allBatches.push({ source: `collector.${resourceTypeKey}.api`, region: region, account: accountId, batches });
            }
        } catch (error) {
            console.error(`Error assuming role:`, error);
            console.warn(`Skipping collection for role ${roleArn}`);
        }
    }
    console.info(`Collected ${resourceType} cross-account resources via Static IAM`);
    return allBatches;
};
