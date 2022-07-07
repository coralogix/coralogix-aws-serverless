/**
 * AWS Kinesis Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.7
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const https = require("https");
const zlib = require("zlib");
const assert = require("assert");

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
const appName = process.env.app_name || "NO_APPLICATION";
const subName = process.env.sub_name || "NO_SUBSYSTEM";
const newlinePattern = process.env.newline_pattern ? RegExp(process.env.newline_pattern) : /(?:\r\n|\r|\n)/g;
const coralogixUrl = process.env.CORALOGIX_URL || "api.coralogix.com";
const bufferCharset = process.env.buffer_charset || "utf8";

/**
 * @description Send logs to Coralogix via API
 * @param {Buffer} logs - GZip compressed logs messages payload
 * @param {function} callback - Function callback
 * @param {int} retryNumber - Retry attempt
 * @param {int} retryLimit - Retry attempts limit
 */
function postToCoralogix(logs, callback, retryNumber = 0, retryLimit = 3) {
    let responseBody = "";

    try {
        const request = https.request({
            hostname: coralogixUrl,
            port: 443,
            path: "/api/v1/logs",
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
                "Content-Length": logs.length
            },
            timeout: 10000
        });

        request.on("response", (response) => {
            console.log("Status: %d", response.statusCode);
            console.log("Headers: %s", JSON.stringify(response.headers));
            response.setEncoding("utf8");
            response.on("data", (chunk) => responseBody += chunk);
            response.on("end", () => {
                if (response.statusCode != 200) throw new Error(responseBody);
                console.log("Body: %s", responseBody);
            });
        });

        request.on("timeout", () => {
            request.destroy();
            if (retryNumber++ < retryLimit) {
                console.log("Problem with request: timeout reached. retrying %d/%d", retryNumber, retryLimit);
                postToCoralogix(logs, callback, retryNumber, retryLimit);
            } else {
                callback(new Error("Failed all retries"));
            }
        });

        request.on("error", callback);

        request.write(logs);
        request.end();
    } catch (error) {
        callback(error);
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
    let resultParsed;
    try {
        resultParsed = event.Records.map((eventRecord) => Buffer.from(eventRecord.kinesis.data, "base64").toString(bufferCharset))
    } catch {
        resultParsed = event.Records.map((eventRecord) => Buffer.from(eventRecord.kinesis.data, "base64").toString("ascii"))
    }
    const parsedEvents = resultParsed.join("\n").split(newlinePattern);

    zlib.gzip(JSON.stringify({
        "privateKey": process.env.private_key,
        "applicationName": appName,
        "subsystemName": subName,
        "logEntries": parsedEvents.map((eventRecord) => {
            return {
                "timestamp": Date.now(),
                "severity": getSeverityLevel(eventRecord),
                "text": eventRecord
            };
        })
    }), (error, compressedEvents) => {
        if (error) {
            callback(error);
        } else {
            postToCoralogix(compressedEvents, callback);
        }
    });
};

exports.handler = handler;
