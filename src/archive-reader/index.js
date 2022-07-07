/**
 * AWS Lambda function for Coralogix archives import
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
    applicationName: "archived-logs",
    subsystemName: "s3-archive-reader"
}));
const logger = new coralogix.CoralogixLogger();

/**
 * @description Send logs records to Coralogix
 * @param {Buffer} content - Logs records data
 */
function sendLogs(content) {
    csv().fromString(content.toString("utf8")).on("data", (row) => {
        let record = JSON.parse(row.toString("utf8"));
        let newRecord;

        try {
            newRecord = JSON.parse(record.text);
        } catch(error) {
            newRecord = {"text": record.text};
        }
        delete record.text;
        newRecord.coralogix_metadata = record;

        logger.addLog(new coralogix.Log({
            text: newRecord,
            severity: getSeverityCode(newRecord.coralogix_metadata.severity)
        }));
    }).on("error", (error) => {
        console.log(error);
    });
}

/**
 * @description Determine severity by name
 * @param {string} severity - Serverity name
 * @returns {int} Severity level
 */
function getSeverityCode(severity) {
    switch (severity) {
        case "Debug":
            return 1;
        case "Verbose":
            return 2;
        case "Info":
            return 3;
        case "Warn":
            return 4;
        case "Error":
            return 5;
        case "Critical":
            return 6;
        default:
            return 3;
    }
}

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    s3.getObject({
        Bucket: event.Records[0].s3.bucket.name,
        Key: decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, " "))
    }, (error, data) => {
        if (error) {
            callback(error);
        } else {
            zlib.gunzip(data.Body, (error, result) => {
                if (error) {
                    callback(error);
                } else {
                    sendLogs(Buffer.from(result));
                    callback(null, data.ContentType);
                }
            });
        }
    });
}

exports.handler = handler;
