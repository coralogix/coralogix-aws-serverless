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

import assert from 'assert'
import { collectLambdaResources } from './lambda.js'
import { collectEc2Resources } from './ec2.js';
import { sendToSqs } from './sqs.js';

const validateAndExtractConfiguration = () => {
    const excludeEC2 = String(process.env.IS_EC2_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true"
    const excludeLambda = String(process.env.IS_LAMBDA_RESOURCE_TYPE_EXCLUDED).toLowerCase() === "true"
    const regions = process.env.REGIONS?.split(',') || [process.env.AWS_REGION];

    return { excludeEC2, excludeLambda, regions };
}
const { excludeEC2, excludeLambda, regions } = validateAndExtractConfiguration();

/**
 * @description Lambda function handler
 */
export const handler = async (_, context) => {
    console.info(`Starting a one-time collection of resources`)

    let collectionPromises = []

    for (const region of regions) {
        if (!excludeEC2) {
            let ec2 = collectEc2ResourceBatches(region)
            collectionPromises.push(ec2)
        }

        if (!excludeLambda) {
            let lambda = collectLambdaResourceBatches(region)
            collectionPromises.push(lambda)
        }
    }

    // Wait for all resources to be collected
    // Otherwise, if sent immediately, there may be an API rate limit exceeded error
    // As the generator will start queueing the Lambda API before the collector is done
    const collectedResources = await Promise.all(collectionPromises)

    for (const { source, region, batches } of collectedResources) {
        for (const batch of batches) {
            console.info(`Sending ${source}-${region} resources batch to SQS`)
            await sendToSqs({ source, region, resources: batch })
            console.info(`Sent ${source}-${region} resources batch to SQS`)
        }
    }

    console.info("Collection done")
}

const collectLambdaResourceBatches = async (region) => {
    console.info(`Collecting Lambda resources in ${region}`)
    const batches = []
    for await (const batch of collectLambdaResources(region)) {
        batches.push(batch)
    }
    return { source: "collector.lambda", region: region, batches }
}

const collectEc2ResourceBatches = async (region) => {
    console.info(`Collecting EC2 resources in ${region}`)
    const batches = []
    for await (const batch of collectEc2Resources(region)) {
        batches.push(batch)
    }
    return { source: "collector.ec2", region: region, batches }
}
