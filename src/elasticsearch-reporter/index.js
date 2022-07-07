/**
 * AWS Lambda function for Coralogix Elasticsearch reports generation
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.8
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const aws = require("aws-sdk");
const assert = require("assert");
const elasticsearch = require("@elastic/elasticsearch");
const jmespath = require("jmespath-plus");
const jsonexport = require("jsonexport");
const nodemailer = require("nodemailer");

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
assert(process.env.query, "No Elasticsearch query!");
assert(process.env.template, "No report template!");
assert(process.env.sender, "No report sender!");
assert(process.env.recipient, "No recipient sender!");
const query = JSON.parse(process.env.query);
const coralogixUrl = process.env.CORALOGIX_URL || "https://coralogix-esapi.coralogix.com:9443";
const requestTimeout = process.env.request_timeout ? parseInt(process.env.request_timeout) : 30000;
const subject = process.env.subject || "Coralogix Elasticsearch Report";
const reportTime = new Date().toISOString();

// Initialize Elasticsearch API client
const es = new elasticsearch.Client({
    node: coralogixUrl,
    maxRetries: 3,
    requestTimeout: requestTimeout
});

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    es.search({
        index: "*",
        body: query
    }, {headers: { "token": process.env.private_key} }, (error, result) => {
        if (error) {
            callback(error);
        } else {
            jsonexport(jmespath.search(result.body, process.env.template), (error, csv) => {
                if (error) {
                    callback(error);
                } else {
                    nodemailer.createTransport({SES: new aws.SES()}).sendMail({
                        from: process.env.sender,
                        to: process.env.recipient,
                        subject: subject,
                        attachments: [
                            {
                                filename: `report_${reportTime}.csv`,
                                content: csv
                            }
                        ]
                    }, (error, info) => {
                        if (error) {
                            callback(error);
                        } else {
                            callback(null, `Report sent successfully: ${info}`);
                        }
                    });
                }
            });
        }
    });
}

exports.handler = handler;
