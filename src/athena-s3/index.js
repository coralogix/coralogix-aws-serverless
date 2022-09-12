/**
 * AWS Lambda function for Coralogix Athena S3
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
const zlib = require("zlib");
const assert = require("assert");
const csv = require("csvtojson");
const coralogix = require("coralogix-logger");
const s3 = new aws.S3();

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");

// Initialize new Coralogix logger
coralogix.CoralogixLogger.configure(new coralogix.LoggerConfig({
    privateKey: process.env.private_key,
    applicationName: process.env.app_name || "NO_APPLICATION",
    subsystemName: process.env.sub_name || "NO_SUBSYSTEM",
    debug: JSON.parse(process.env.debug || false)
}));
const logger = new coralogix.CoralogixLogger();

/**
 * @description Send logs records to Coralogix
 * @param {Buffer} content - Logs records data
 */
function sendLogs(content) {
    csv().fromString(content.toString("utf8")).on("data", (row) => {
        logger.addLog(new coralogix.Log({
            text: row.toString("utf8")
        }));
    }).on("error", (error) => {
        console.log(error);
    });
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
                sendLogs(Buffer.from(data.Body))
            }
        }
    });
}

exports.handler = handler;
