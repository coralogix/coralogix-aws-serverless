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

import { collectLambdaResources, parseLambdaFunctionArn } from './lambda.js'
import { sendToCoralogix } from './coralogix.js'
import { collectEc2Resources } from './ec2.js';

const validateAndExtractConfiguration = () => {
    const filterEC2= String(process.env.RESOURCE_TYPE_FILTER).toLowerCase() === 'ec2';
    const filterLambda= String(process.env.RESOURCE_TYPE_FILTER).toLowerCase() === 'lambda';
    return { filterEC2, filterLambda };
}
const { filterEC2, filterLambda } = validateAndExtractConfiguration();

/**
 * @description Lambda function handler
 */
export const handler = async (_, context) => {
    const invokedArn = parseLambdaFunctionArn(context.invokedFunctionArn) // The invoked arn may contain a version or an alias
    const collectorId = `arn:aws:lambda:${invokedArn.region}:${invokedArn.accountId}:function:${invokedArn.functionName}`
    console.info(`Collector ${collectorId} starting collection`)

    const lambda = collectAndSendLambdaResources(collectorId)
    const ec2 = collectAndSendEc2Resources(collectorId, invokedArn.region, invokedArn.accountId)

    let dataToCollect = []
    if(!filterEC2) dataToCollect.push(ec2)
    if(!filterLambda) dataToCollect.push(lambda)
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