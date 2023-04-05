/**
 * AWS Resource Tags Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     0.1.0
 * @since       0.1.0
 */

"use strict";

import { collectLambdaResources } from './lambda.js'
import { sendToCoralogix } from './coralogix.js'

/**
 * @description Lambda function handler
 */
export const handler = async () => {
    const collectorId = "resource-metadata"

    console.info("Collecting Lambda resources")
    const lambdaResources = await collectLambdaResources()
    console.info("Sending Lambda resources to coralogix")
    await sendToCoralogix({ collectorId, resources: lambdaResources })

    // TODO EC2 metadata collection

    console.info("Done")
}
