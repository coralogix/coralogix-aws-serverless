/**
 * AWS S3 Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.1
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const aws = require("aws-sdk");
const zlib = require("zlib");
const assert = require("assert");
const coralogix = require("coralogix-logger");
const s3 = new aws.S3();

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
const appName = process.env.app_name || "NO_APPLICATION";
const subName = process.env.sub_name || "NO_SUBSYSTEM";
const newlinePattern = process.env.newline_pattern ? RegExp(process.env.newline_pattern) : /(?:\r\n|\r|\n)/g;

// Initialize new Coralogix logger
coralogix.CoralogixLogger.configure(new coralogix.LoggerConfig({
    privateKey: process.env.private_key,
    applicationName: appName,
    subsystemName: subName
}));
const logger = new coralogix.CoralogixLogger(appName);

/**
 * @description Send logs records to Coralogix
 * @param {Buffer} content - Logs records data
 */
function sendLogs(content) {
    const logs = content.toString("utf8").split(newlinePattern);
    for (let i = 0; i < logs.length; i++) {
        if (!logs[i]) continue;
        const log = new coralogix.Log({
            text: logs[i],
            severity: getSeverityLevel(logs[i])
        });
        logger.addLog(log);
    }
}

/**
 * @description Extract serverity from log record
 * @param {string} message - Log message
 * @returns {int} Severity level
 */
function getSeverityLevel(message) {
    let severity = 3;
    if (!message)
        return severity;
    if (message.includes("Warning") || message.includes("warn"))
        severity = 4;
    if (message.includes("Error") || message.includes("Exception"))
        severity = 5;
    return severity;
}

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    const bucket = event.Records[0].s3.bucket.name;
    const key = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, " "));

    s3.getObject({
        Bucket: bucket,
        Key: key
    }, (error, data) => {
        if (error) {
            callback(error);
        } else {
            if (data.ContentType == "application/octet-stream" ||
                data.ContentType == "application/x-gzip" ||
                data.ContentEncoding == "gzip" ||
                data.ContentEncoding == "compress" ||
                key.endsWith(".gz")
            ) {
                zlib.gunzip(data.Body, (error, result) => {
                    if (error) {
                        callback(error);
                    } else {
                        sendLogs(Buffer.from(result));
                        callback(null, data.ContentType);
                    }
                });
            } else {
                sendLogs(Buffer.from(data.Body))
            }
        }
    });
}

exports.handler = handler;
