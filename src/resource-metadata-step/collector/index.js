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

import { collectLambdaResources, parseLambdaFunctionArn } from '../generator/lambda.js'
import { sendToCoralogix } from '../generator/coralogix.js'
import { collectEc2Resources } from '../generator/ec2.js';

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
    const invokedArn = parseLambdaFunctionArn(context.invokedFunctionArn) // The invoked arn may contain a version or an alias
    const collectorId = `arn:aws:lambda:${invokedArn.region}:${invokedArn.accountId}:function:${invokedArn.functionName}`
    console.info(`Collector ${collectorId} starting collection`)

    let dataToCollect = []

    if (!excludeEC2) {
        const ec2 = collectAndSendEc2Resources(collectorId, invokedArn.region, invokedArn.accountId)
        dataToCollect.push(ec2)
    }

    if (!excludeLambda) {
        const lambda = collectAndSendLambdaResources(collectorId)
        dataToCollect.push(lambda)
    }
    await Promise.all(dataToCollect)

    console.info("Collection done")
}

const collectAndSendLambdaResources = async (collectorId) => {
    console.info("Collecting Lambda resources")
    const lambdaResources = await collectLambdaResources()
    console.info("Sending Lambda resources to coralogix")
    await sendToCoralogix({ collectorId, resources: lambdaResources })
    console.info("Sent Lambda resources to coralogix")
}

const collectAndSendEc2Resources = async (collectorId, region, accountId) => {
    console.info("Collecting EC2 resources")
    const ec2Resources = await collectEc2Resources(region, accountId)
    console.info("Sending EC2 resources to coralogix")
    await sendToCoralogix({ collectorId, resources: ec2Resources })
    console.info("Sent EC2 resources to coralogix")
}