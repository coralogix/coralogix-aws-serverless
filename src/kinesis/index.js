/**
 * AWS Kinesis Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.0
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const https = require("https");
const assert = require("assert");

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
const appName = process.env.app_name || "NO_APPLICATION";
const subName = process.env.sub_name || "NO_SUBSYSTEM";
const newlinePattern = process.env.newline_pattern ? RegExp(process.env.newline_pattern) : /(?:\r\n|\r|\n)/g;
const coralogixUrl = process.env.CORALOGIX_URL || "api.coralogix.com";

/**
 * Decode payload to simple string
 * @param {string} streamEventRecord - Kinesis data payload
 * @returns {string} Decoded payload
 */
function extractEvent(streamEventRecord) {
    return new Buffer(streamEventRecord.kinesis.data, "base64").toString("ascii");
}

/**
 * @description Split payload to records
 * @param {string} eventsData - Kinesis data payload
 * @returns {Array} Log records
 */
function parseEvents(eventsData) {
    return eventsData.split(newlinePattern).map((eventRecord) => {
        return {
            "timestamp": Date.now(),
            "severity": getSeverityLevel(eventRecord),
            "text": eventRecord
        };
    });
}

/**
 * @description Send logs to Coralogix via API
 * @param {object} parsedEvents - Logs messages
 */
function postEventsToCoralogix(parsedEvents) {
    try {
        let retries = 3;
        let timeout = 10000;
        let retryNumber = 0;
        let sendRequest = function sendRequest() {
            let request = https.request({
                hostname: coralogixUrl,
                port: 443,
                path: "/api/v1/logs",
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            }, (response) => {
                console.log("Status: %d", response.statusCode);
                console.log("Headers: %s", JSON.stringify(respose.headers));
                response.setEncoding("utf8");
                response.on("data", (body) => {
                    console.log("Body: %s", body);
                });
            });

            request.setTimeout(timeout, () => {
                request.abort();
                if (retryNumber++ < retries) {
                    console.log("Problem with request: timeout reached. retrying %d/%d", retryNumber, retries);
                    sendRequest();
                } else {
                    console.log("Problem with request: timeout reached. failed all retries.");
                }
            });

            request.on("error", (error) => {
                console.log("Problem with request: %s", error.message);
            });

            request.write(JSON.stringify(parsedEvents));
            request.end();
        };
        sendRequest();
    } catch (error) {
        console.log(error.message);
    }
}

/**
 * @description Extract serverity from log record
 * @param {string} message - Log message
 * @returns {int} Severity level
 */
function getSeverityLevel(message) {
    let severity = 3;
    if (message.includes("debug"))
        severity = 1;
    if (message.includes("verbose"))
        severity = 2;
    if (message.includes("info"))
        severity = 3;
    if (message.includes("warn") || message.includes("warning"))
        severity = 4;
    if (message.includes("error"))
        severity = 5;
    if (message.includes("critical") || message.includes("panic"))
        severity = 6;
    return severity;
}

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    postEventsToCoralogix({
        "privateKey": process.env.private_key,
        "applicationName": appName,
        "subsystemName": subName,
        "logEntries": parseEvents(event.Records.map(extractEvent).join("\n"))
    });
};

exports.handler = handler;
