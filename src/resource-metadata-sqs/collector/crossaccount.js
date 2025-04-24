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
import { ConfigServiceClient, SelectResourceConfigCommand } from "@aws-sdk/client-config-service";

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
export const collectLambdaResourcesViaConfig = async (configAggregatorName) => {
    console.info("Collecting Lambda resources via AWS Config");
    try {
        const configClient = new ConfigServiceClient({ region: process.env.AWS_REGION });
        const batchSize = 100;

        // Query to find all Lambda functions across accounts and regions
        const baseQuery = "SELECT resourceId, resourceName, resourceType, awsRegion, accountId WHERE resourceType = 'AWS::Lambda::Function'";

        let nextToken;
        let allBatches = [];
        let totalFunctions = 0;

        // Paginate through all results
        do {
            const command = new SelectResourceConfigCommand({
                Expression: baseQuery,
                ConfigurationAggregator: configAggregatorName,
                Limit: batchSize,
                NextToken: nextToken
            });

            const response = await configClient.send(command);
            nextToken = response.NextToken;

            // Process results
            if (response.Results && response.Results.length > 0) {
                const batch = [];

                for (const resultString of response.Results) {
                    const result = JSON.parse(resultString);

                    // Format function data to match the expected structure
                    batch.push({
                        functionArn: result.resourceId,
                        functionName: result.resourceName,
                        // Add other needed properties that your generator expects
                    });
                }

                // Organize results by account and region to match the expected output format
                const batchesByAccountAndRegion = {};

                for (const func of batch) {
                    // Extract account and region from ARN
                    // ARN format: arn:aws:lambda:region:account-id:function:function-name
                    const arnParts = func.functionArn.split(':');
                    const region = arnParts[3];
                    const account = arnParts[4];

                    const key = `${account}:${region}`;
                    if (!batchesByAccountAndRegion[key]) {
                        batchesByAccountAndRegion[key] = {
                            source: "collector.lambda",
                            region,
                            account,
                            batches: []
                        };
                    }

                    // Add batch if it reaches reasonable size or is the last batch
                    if (!batchesByAccountAndRegion[key].batches[0]) {
                        batchesByAccountAndRegion[key].batches.push([]);
                    }

                    batchesByAccountAndRegion[key].batches[0].push(func);
                    totalFunctions++;
                }

                // Add organized batches to the result
                for (const key in batchesByAccountAndRegion) {
                    allBatches.push(batchesByAccountAndRegion[key]);
                }
            }
        } while (nextToken);

        console.info(`Collected ${totalFunctions} Lambda functions via AWS Config`);
        return allBatches;
    } catch (error) {
        console.error("Error collecting Lambda functions via AWS Config:", error);
        return null; // Return null to indicate failure
    }
};

// Helper function to collect via Static IAM roles
export const collectViaStaticIAM = async (collectionPromises, roleArns, regions, excludeEC2, excludeLambda, collectEc2ResourceBatches, collectLambdaResourceBatches) => {
    for (const roleArn of roleArns) {
        try {
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
        } catch (error) {
            console.error(`Error assuming role ${roleArn}:`, error);
            console.warn(`Skipping collection for role ${roleArn}`);
        }
    }
};
