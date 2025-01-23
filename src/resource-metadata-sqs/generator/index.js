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

import { generateLambdaResources, parseLambdaFunctionArn } from './lambda.js'
import { sendToCoralogix } from './coralogix.js'
import { generateEc2Resources } from './ec2.js';

/**
 * @description Lambda function handler
 */

export const handler = async (event, context) => {
    // Handle SQS events which come in a Records array
    if (event.Records) {
        console.info(`Processing ${event.Records.length} SQS messages`)
        const batchItemFailures = []

        for (const record of event.Records) {
            // ensure partial batch processing
            try {
                const messageBody = JSON.parse(record.body)
                await processMessage(messageBody, context)
            } catch (error) {
                console.error(`Failed to process message: ${error}`)
                batchItemFailures.push({ itemIdentifier: record.messageId })
            }
        }

        return { batchItemFailures }
    }

    // Handle direct invocation
    await processMessage(event, context)
}

const processMessage = async (event, context) => {
    console.debug(event)
    if (!event.source) {
        throw new Error("Event source property is missing")
    }

    const invokedArn = parseLambdaFunctionArn(context.invokedFunctionArn)
    const collectorId = `arn:aws:lambda:${invokedArn.region}:${invokedArn.accountId}:function:${invokedArn.functionName}`
    console.info(`Collector ${collectorId} starting collection`)

    switch (event.source.toLowerCase()) {
        case "collector.ec2":
            await generateAndSendEc2Resources(collectorId, invokedArn.region, invokedArn.accountId, event.resources, "create")
            break
        case "collector.lambda":
            await generateAndSendLambdaResources(collectorId, invokedArn.region, invokedArn.accountId, event.resources, "create")
            break
        case "aws.ec2":
            const mode = event.detail.eventName === "TerminateInstances" ? "delete" : "create"
            await generateAndSendEc2Resources(collectorId, invokedArn.region, invokedArn.accountId, event.detail.responseElements.instancesSet.items, mode)
            break
        case "aws.lambda":
            const resource = event.detail.eventName === "DeleteFunction20150331" ? [event.detail.requestParameters] : [event.detail.responseElements]
            const lambdaMode = event.detail.eventName === "DeleteFunction20150331" ? "delete" : "create"
            await generateAndSendLambdaResources(collectorId, invokedArn.region, invokedArn.accountId, resource, lambdaMode)
            break
        default:
            throw new Error(`Unsupported event type: ${event.type}`)
    }

    console.info("Collection done")
}

const generateAndSendLambdaResources = async (collectorId, region, accountId, resources, mode) => {
    console.info("Generating Lambda resources")
    const lambdaResources = await generateLambdaResources(region, accountId, resources, mode)
    console.info("Sending Lambda resources to coralogix")
    await sendToCoralogix({ collectorId, resources: lambdaResources })
    console.info("Sent Lambda resources to coralogix")
}

const generateAndSendEc2Resources = async (collectorId, region, accountId, resources, mode) => {
    console.info("Generating EC2 resources")
    const ec2Resources = await generateEc2Resources(region, accountId, resources, mode)
    console.info("Sending EC2 resources to coralogix")
    await sendToCoralogix({ collectorId, resources: ec2Resources })
    console.info("Sent EC2 resources to coralogix")
}
