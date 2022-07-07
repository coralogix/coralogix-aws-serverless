/**
 * Akamai DataStream Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.6
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const aws = require("aws-sdk");
const assert = require("assert");
const coralogix = require("coralogix-logger");
const EdgeGrid = require("edgegrid");
const lambda = new aws.Lambda();

// Check Lambda function parameters
assert(process.env.CORALOGIX_PRIVATE_KEY, "No Coralogix Private Key!");
assert(process.env.AKAMAI_CLIENT_TOKEN, "Akamai Client Token is not set");
assert(process.env.AKAMAI_CLIENT_SECRET, "Akamai Client Secret is not set");
assert(process.env.AKAMAI_ACCESS_TOKEN, "Akamai Access Token is not set");
assert(process.env.AKAMAI_HOST, "Akamai Host is not set");
assert(process.env.AKAMAI_STREAM_ID, "Akamai DataStream ID is not set");
assert(process.env.AKAMAI_LOGS_TYPE, "Akamai DataStream logs type is not set");
assert(
    ["raw-logs", "aggregate-logs"].includes(process.env.AKAMAI_LOGS_TYPE),
    "Akamai DataStream logs type is invalid"
);
const appName = process.env.CORALOGIX_APP_NAME || "Akamai";
const subName = process.env.CORALOGIX_SUB_SYSTEM || "DataStream";

// Initialize Akamai API client
const eg = new EdgeGrid(
    process.env.AKAMAI_CLIENT_TOKEN,
    process.env.AKAMAI_CLIENT_SECRET,
    process.env.AKAMAI_ACCESS_TOKEN,
    process.env.AKAMAI_HOST,
);

// Initialize new Coralogix logger
coralogix.CoralogixLogger.configure(new coralogix.LoggerConfig({
    privateKey: process.env.CORALOGIX_PRIVATE_KEY,
    applicationName: appName,
    subsystemName: subName
}));
const logger = new coralogix.CoralogixLogger(appName);

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    lambda.getFunction({
        FunctionName: context.functionName
    }, (error, func) => {
        if (error) {
            callback(error);
        } else {
            const stream_id = process.env.AKAMAI_STREAM_ID;
            const logs_type = process.env.AKAMAI_LOGS_TYPE;
            let start = new Date();
            let end = new Date();

            start.setMinutes(end.getMinutes() - 15);
            end.setMinutes(end.getMinutes() - 1);

            start = start.toISOString().split(".").shift() + "Z";
            end = end.toISOString().split(".").shift() + "Z";

            eg.auth({
                path: `/datastream-pull-api/v1/streams/${stream_id}/${logs_type}`,
                method: "GET",
                qs: {
                    "start": func.Tags["akamai:lastDataInvocation"] || start,
                    "end": end,
                    "size": process.env.AKAMAI_MAX_RECORDS_LIMIT || 2000
                }
            }).send((error, response, body) => {
                if (error) {
                    callback(error);
                } else if (response.statusCode == 204) {
                    callback(null, "No new data arrived");
                } else if (response.statusCode != 200) {
                    callback(new Error(`Request failed [${response.statusCode}]: ${body}`));
                } else {
                    JSON.parse(body).data.forEach((record) => {
                        logger.addLog(new coralogix.Log({
                            severity: coralogix.Severity.info,
                            text: JSON.stringify(record),
                            category: logs_type,
                            threadId: stream_id
                        }));
                    });
                    lambda.tagResource({
                        Resource: func.Configuration.FunctionArn,
                        Tags: {
                            "akamai:lastDataInvocation": end
                        }
                    }, (error, tags) => {
                        if (error) {
                            callback(error);
                        } else {
                            callback(null, end);
                        }
                    });
                }
            });
        }
    });
}

exports.handler = handler;
