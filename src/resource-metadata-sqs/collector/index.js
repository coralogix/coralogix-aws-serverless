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

import { collectLambdaResources } from './lambda.js'
import { collectEc2Resources } from './ec2.js';
import { sendToSqs } from './sqs.js';

const validateAndExtractConfiguration = () => {
    const excludeEC2 = String(process.env.IS_EC2_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true"
    const excludeLambda = String(process.env.IS_LAMBDA_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true"
    return { excludeEC2, excludeLambda };
}
const { excludeEC2, excludeLambda } = validateAndExtractConfiguration();

/**
 * @description Lambda function handler
 */
export const handler = async (_, context) => {
    console.info(`Starting a one-time collection of resources`)

    let collectionPromises = []

    if (!excludeEC2) {
        const ec2 = collectEc2ResourceBatches()
        collectionPromises.push(ec2)
    }

    if (!excludeLambda) {
        const lambda = collectLambdaResourceBatches()
        collectionPromises.push(lambda)
    }

    // Wait for all resources to be collected
    // Otherwise, if sent immediately, there may be an API rate limit exceeded error
    // As the generator will start queueing the Lambda API before the collector is done
    const collectedResources = await Promise.all(collectionPromises)

    for (const { source, batches } of collectedResources) {
        for (const batch of batches) {
            console.info(`Sending ${source} resources batch to SQS`)
            await sendToSqs({ source, resources: batch })
            console.info(`Sent ${source} resources batch to SQS`)
        }
    }

    console.info("Collection done")
}

const collectLambdaResourceBatches = async () => {
    console.info("Collecting Lambda resources")
    const batches = []
    for await (const batch of collectLambdaResources()) {
        batches.push(batch)
    }
    return { source: "collector.lambda", batches }
}

const collectEc2ResourceBatches = async () => {
    console.info("Collecting EC2 resources")
    const batches = []
    for await (const batch of collectEc2Resources()) {
        batches.push(batch)
    }
    return { source: "collector.ec2", batches }
}
