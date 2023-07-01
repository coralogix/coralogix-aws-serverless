const aws = require('aws-sdk');
const coralogix = require("coralogix-logger");
const assert = require("assert");

"use strict";

// Check Lambda function parameters

assert(process.env.private_key, "No private key!");
const appName = process.env.app_name || "NO_APPLICATION";
const subName = process.env.sub_name || "NO_SUBSYSTEM";


// Create an instance of the ECR service client
const ecr = new aws.ECR();

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

    ecr.describeImageScanFindings({ repositoryName, imageId }, (err, data) => {
      if (err) {
        callback(err);;
      } else {
        const findings = data['imageScanFindings']['findings'];
        for (let i = 0; i < findings.length; i++) {
            const log = {
                "metadata": {
                    "repository": repositoryName,
                    "image_id": imageId,
                    "image_tags": event['detail']['image-tags']
                },
                "findings": findings[i]
            }
            sendLogs(log);
        }
      }
    });
}

exports.handler = handler;
