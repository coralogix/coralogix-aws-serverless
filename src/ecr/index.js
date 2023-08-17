/**
 * AWS Container Registry Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.5
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const aws = require('aws-sdk');
const coralogix = require("coralogix-logger");
const assert = require("assert");
const ecr = new aws.ECR();

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
const appName = process.env.app_name || "NO_APPLICATION";
const subName = process.env.sub_name || "NO_SUBSYSTEM";

// Initialize new Coralogix logger
coralogix.CoralogixLogger.configure(new coralogix.LoggerConfig({
    privateKey: process.env.private_key,
    applicationName: appName,
    subsystemName: subName
}));
const logger = new coralogix.CoralogixLogger(appName);

// Send logs to Coralogix
function sendLogs(content) {
    try {
        const log = content;
        const logToSend = new coralogix.Log({
                text: JSON.stringify(log),
                severity: 3
            })
            logger.addLog(logToSend);
    } catch (error) {
        console.log(error);
    }
}

// Call the describeImageScanFindings method
function handler(event, context, callback) {
    const repositoryName = event['detail']['repository-name'];
    const imageId = { imageDigest: event['detail']['image-digest'] };
    const maxResults = 1000;

    ecr.describeImageScanFindings({ repositoryName, imageId, maxResults }, (err, data) => {
      if (err) {
        callback(err);
      } else {
        const findings = data['imageScanFindings']['findings'];
        let summary_log = {"ecr_scan_summary": event['detail']};
        sendLogs(summary_log);

        for ( let i = 0 ; i < findings.length ; i++ ) {
            let package_name = "NO_PACKAGE";
            let package_version = "NO_VERSION";

            for ( let j = 0 ; findings[i].hasOwnProperty("attributes") && i < findings[i].attributes.length ; i++ ) {
                if (package_name === "NO_PACKAGE") {
                    package_name = findings[i].attributes[j].key == "package_name" ? findings[i].attributes[j].value : "NO_PACKAGE" ;
                }
                if (package_version === "NO_VERSION") {
                    package_version = findings[i].attributes[j].key == "package_version" ? findings[i].attributes[j].value : "NO_VERSION" ;
                }
                if (package_version !== "NO_VERSION" && package_name !== "NO_PACKAGE") {
                   break
                }
            }
            const log = {
                "metadata": {
                    "repository": repositoryName,
                    "image_id": imageId,
                    "image_tags": event['detail']['image-tags']
                },
                "findings": {
                    "package": package_name + ":" + package_version,
                    "details": findings[i]
                }
            }
            sendLogs(log);
        }
      }
    });
}

exports.handler = handler;
