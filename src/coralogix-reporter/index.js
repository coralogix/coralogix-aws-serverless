/**
 * AWS Lambda function for Coralogix OpenSearch reports generation
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     2.0.2
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const sesClientModule = require("@aws-sdk/client-ses");
const assert = require("assert");
const opensearch = require("@opensearch-project/opensearch");
const jmespath = require("jmespath-plus");
const jsonexport = require("jsonexport");
const nodemailer = require("nodemailer");

// Check Lambda function parameters
assert(process.env.logs_query_key, "No Logs Query key!");
assert(process.env.query, "No OpenSearch query!");
assert(process.env.template, "No report template!");
assert(process.env.sender, "No report sender!");
assert(process.env.recipient, "No recipient sender!");
const query = JSON.parse(process.env.query);
const coralogixUrl = process.env.CORALOGIX_URL || "https://coralogix-esapi.coralogix.com:9443";
const requestTimeout = process.env.request_timeout ? parseInt(process.env.request_timeout) : 30000;
const subject = process.env.subject || "Coralogix OpenSearch Report";

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    const reportTime = new Date().toISOString();

    // Initialize OpenSearch API client
    const searchClient = new opensearch.Client({
        node: coralogixUrl,
        maxRetries: 3,
        requestTimeout: requestTimeout
    });

    searchClient.search({
        index: "*",
        body: query
    }, {headers: { "token": process.env.logs_query_key} }, (error, result) => {
        if (error) {
            callback(error);
        } else {
            jsonexport(jmespath.search(result.body, process.env.template), (error, csv) => {
                if (error) {
                    callback(error);
                } else {
                    const ses = new sesClientModule.SESClient({});
                    nodemailer.createTransport({
                        SES: { ses, aws: sesClientModule },
                     }).sendMail({
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
