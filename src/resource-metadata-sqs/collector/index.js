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

import { collectLambdaResources } from './lambda.js';
import { collectEc2Resources } from './ec2.js';
import { sendToSqs } from './sqs.js';
import { getAccountId, collectLambdaResourcesViaConfig, collectViaStaticIAM } from './crossaccount.js';

const CROSS_ACCOUNT_MODE = {
    DISABLED: 'Disabled',
    STATIC_IAM: 'StaticIAM',
    CONFIG: 'Config'
};

const validateAndExtractConfiguration = () => {
    const excludeEC2 = String(process.env.IS_EC2_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true";
    const excludeLambda = String(process.env.IS_LAMBDA_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true";
    const regions = process.env.REGIONS?.split(',') || [process.env.AWS_REGION];
    const roleArns = process.env.CROSSACCOUNT_IAM_ROLE_ARNS ? process.env.CROSSACCOUNT_IAM_ROLE_ARNS.split(',') : [];

    // Extract cross-account mode from environment variable
    const crossAccountMode = process.env.CROSS_ACCOUNT_MODE || CROSS_ACCOUNT_MODE.DISABLED;

    // Config aggregator name (only used when crossAccountMode is CONFIG)
    const configAggregatorName = process.env.CONFIG_AGGREGATOR_NAME || 'OrganizationAggregator';

    return { excludeEC2, excludeLambda, regions, roleArns, crossAccountMode, configAggregatorName };
};

const { excludeEC2, excludeLambda, regions, roleArns, crossAccountMode, configAggregatorName } = validateAndExtractConfiguration();

/**
 * @description Lambda function handler
 */
export const handler = async (_, context) => {
    console.info(`Starting a one-time collection of resources`);
    console.info(`Cross account mode: ${crossAccountMode}`);

    let collectionPromises = [];

    // Collect resources from the current account - always happens regardless of cross-account mode
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

    // Handle cross-account collection based on the selected mode
    if (crossAccountMode === CROSS_ACCOUNT_MODE.CONFIG) {
        try {
            // Try to collect via Config first
            const configResults = await collectLambdaResourcesViaConfig(configAggregatorName);

            if (configResults) {
                // Successfully collected via Config, add to our collection promises
                collectionPromises = [...collectionPromises, ...configResults];
                console.info("Successfully collected cross-account resources via AWS Config");
            } else {
                // Config collection failed, fall back to StaticIAM if roleArns are provided
                console.warn("AWS Config collection failed, checking for fallback options");
                if (roleArns.length > 0) {
                    console.info("Falling back to Static IAM approach");
                    await collectViaStaticIAM(
                        collectionPromises,
                        roleArns,
                        regions,
                        excludeEC2,
                        excludeLambda,
                        collectEc2ResourceBatches,
                        collectLambdaResourceBatches
                    );
                } else {
                    console.warn("No fallback options available, continuing with current account only");
                }
            }
        } catch (error) {
            console.error("Error in Config collection:", error);
            // Fall back to StaticIAM if available
            if (roleArns.length > 0) {
                console.info("Falling back to Static IAM approach");
                await collectViaStaticIAM(
                    collectionPromises,
                    roleArns,
                    regions,
                    excludeEC2,
                    excludeLambda,
                    collectEc2ResourceBatches,
                    collectLambdaResourceBatches
                );
            } else {
                console.warn("No fallback options available, continuing with current account only");
            }
        }
    } else if (crossAccountMode === CROSS_ACCOUNT_MODE.STATIC_IAM) {
        // Use the existing Static IAM approach
        await collectViaStaticIAM(
            collectionPromises,
            roleArns,
            regions,
            excludeEC2,
            excludeLambda,
            collectEc2ResourceBatches,
            collectLambdaResourceBatches
        );
    } else {
        console.info("Cross-account collection is disabled");
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
