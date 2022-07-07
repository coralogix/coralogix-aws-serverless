/**
 * AWS SNS Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.3
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const https = require("https");
const zlib = require("zlib");
const assert = require("assert");

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
const coralogixUrl = process.env.CORALOGIX_URL || "api.coralogix.com";

/**
 * @description Send logs to Coralogix via API
 * @param {Buffer} logs - GZip compressed logs messages payload
 * @param {function} callback - Function callback
 * @param {number} retryNumber - Retry attempt
 * @param {number} retryLimit - Retry attempts limit
 */
function postToCoralogix(logs, callback, retryNumber = 0, retryLimit = 3) {
    let responseBody = "";

    try {
        const request = https.request({
            hostname: coralogixUrl,
            port: 443,
            path: "/logs/rest/singles",
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
                "Content-Length": logs.length,
                "private_key": process.env.private_key
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
 * @description Extract nested field from object
 * @param {string} path - Path to field
 * @param {*} object - JavaScript object
 * @returns {*} Field value
 */
function dig(path, object) {
    if (path.startsWith("$.")) {
        return path.split(".").slice(1).reduce((xs, x) => (xs && xs[x]) ? xs[x] : path, object);
    }
    return path;
}

/**
 * @description Extract serverity from log record
 * @param {string} message - Log message
 * @returns {number} Severity level
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
 * @param {function} callback - Function callback
 */
function handler(event, context, callback) {
    zlib.gzip(JSON.stringify(
        event.Records.map(logEvent => logEvent.Sns).filter((logEvent) => logEvent.Message.length > 0).map((logEvent) => {
            let appName = process.env.app_name || "NO_APPLICATION";
            let subName = process.env.sub_name || "NO_SUBSYSTEM";

            try {
                appName = appName.startsWith("$.") ? dig(appName, logEvent) : appName;
                subName = subName.startsWith("$.") ? dig(subName, logEvent) : subName;
            } catch {}

            return {
                "applicationName": appName,
                "subsystemName": subName,
                "timestamp": Date.parse(logEvent.Timestamp),
                "severity": getSeverityLevel(logEvent.Message.toLowerCase()),
                "text": logEvent.Message,
                "category": logEvent.Subject,
                "threadId": logEvent.TopicArn
            };
        })
    ), (error, compressedEvents) => {
        if (error) {
            callback(error);
        } else {
            postToCoralogix(compressedEvents, callback);
        }
    });
}

exports.handler = handler;
