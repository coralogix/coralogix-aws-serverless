/**
 * AWS S3-via-SNS Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.21
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
const newlinePattern = process.env.newline_pattern ? RegExp(process.env.newline_pattern) : /(?:\r\n|\r|\n)/g;
const blockingPattern = process.env.blocking_pattern ? RegExp(process.env.blocking_pattern) : null;
const sampling = process.env.sampling ? parseInt(process.env.sampling) : 1;
const debug = JSON.parse(process.env.debug || false);

// Initialize new Coralogix logger
coralogix.CoralogixCentralLogger.configure(new coralogix.LoggerConfig({
    privateKey: process.env.private_key,
    debug: debug
}));
const logger = new coralogix.CoralogixCentralLogger();

/**
 * @description Send logs records to Coralogix
 * @param {Buffer} content - Logs records data
 * @param {string} filename - Logs filename S3 path
 */
function sendLogs(content, filename) {
    const logs = content.toString("utf8").split(newlinePattern);

    for (let i = 0; i < logs.length; i += sampling) {
        if (!logs[i]) continue;
        if (blockingPattern && logs[i].match(blockingPattern)) continue;
        let appName = process.env.app_name || "NO_APPLICATION";
        let subName = process.env.sub_name || "NO_SUBSYSTEM";

        try {
            appName = appName.startsWith("$.") ? dig(appName, JSON.parse(logs[i])) : appName;
            subName = subName.startsWith("$.") ? dig(subName, JSON.parse(logs[i])) : subName;
        } catch {}

        logger.addLog(
            appName,
            subName,
            new coralogix.Log({
                severity: getSeverityLevel(logs[i]),
                text: logs[i],
                threadId: filename
            })
        );
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
    const s3_event = JSON.parse(event.Records[0].Sns.Message);
    console.log(event.Records[0].Sns.Message);
    const bucket = s3_event.Records[0].s3.bucket.name;
    const key = decodeURIComponent(s3_event.Records[0].s3.object.key.replace(/\+/g, " "));

    s3.getObject({
        Bucket: bucket,
        Key: key
    }, (error, data) => {
        if (error) {
            callback(error);
        } else {
            if (data.ContentType == "application/x-gzip" ||
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
                sendLogs(Buffer.from(data.Body), `s3://${bucket}/${key}`);
            }
        }
    });
}

exports.handler = handler;
