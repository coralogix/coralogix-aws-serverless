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

import { collectLambdaResources } from 'lambda.js'
import { collectEc2Resources } from 'ec2.js';
import { sendToSqs } from 'sqs.js';

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

    let dataToCollect = []

    if (!excludeEC2) {
        const ec2 = collectAndSendEc2Resources()
        dataToCollect.push(ec2)
    }

    if (!excludeLambda) {
        const lambda = collectAndSendLambdaResources()
        dataToCollect.push(lambda)
    }
    await Promise.all(dataToCollect)

    console.info("Collection done")
}

const collectAndSendLambdaResources = async () => {
    console.info("Collecting Lambda resources")
    const lambdaResources = await collectLambdaResources()
    console.info("Sending Lambda resources to SQS")
    await sendToSqs({ resources: lambdaResources })
    console.info("Sent Lambda resources to SQS")
}

const collectAndSendEc2Resources = async () => {
    console.info("Collecting EC2 resources")
    const ec2Resources = await collectEc2Resources()
    console.info("Sending EC2 resources to SQS")
    await sendToSqs({ resources: ec2Resources })
    console.info("Sent EC2 resources to SQS")
}
