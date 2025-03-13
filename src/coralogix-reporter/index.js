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
assert(process.env.api_key, "No API key!");
assert(process.env.query, "No OpenSearch query!");
assert(process.env.template, "No report template!");
assert(process.env.sender, "No report sender!");
assert(process.env.recipient, "No recipient sender!");
assert(process.env.coralogix_endpoint, "No Coralogix endpoint!");
const query = JSON.parse(process.env.query);
const requestTimeout = process.env.request_timeout ? parseInt(process.env.request_timeout) : 30000;
const subject = process.env.subject || "Coralogix OpenSearch Report";

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @returns {Promise<string>} Function result
 */
async function handler(event, context) {
    console.log('Handler started');
    const reportTime = new Date().toISOString();

    console.log('Initializing OpenSearch client');
    const searchClient = new opensearch.Client({
        node: process.env.coralogix_endpoint,
        maxRetries: 3,
        requestTimeout: requestTimeout,
        headers: {
            'Authorization': `Bearer ${process.env.api_key}`
        }
    });

    try {
        console.log('Configuration:', {
            coralogixEndpoint: process.env.coralogix_endpoint,
            requestTimeout,
            sender: process.env.sender,
            recipient: process.env.recipient,
            region: process.env.AWS_REGION
        });

        console.log('Executing OpenSearch query');
        const result = await searchClient.search({
            index: "*",
            body: query
        });

        let responseBody;
        if (typeof result.body === 'string') {
            try {
                responseBody = JSON.parse(result.body);
                console.log('Parsed response body aggregations');
            } catch (e) {
                console.error('Failed to parse response body:', e);
                throw e;
            }
        } else {
            responseBody = result.body;
        }

        // Debug the complete response
        // console.log('Full OpenSearch response:', JSON.stringify(result));

        console.log('Converting results to CSV');
        const csv = await new Promise((resolve, reject) => {
            const templateResult = jmespath.search(responseBody, process.env.template);
            console.log('Data after JMESPath template:', JSON.stringify(templateResult));

            // If response is empty – exit function before attempting to convert to CSV and send email
            if (!templateResult || (Array.isArray(templateResult) && templateResult.length === 0)) {
                console.log('No results found after template application');
                resolve('No data found\n');
                return;
            }

            jsonexport(templateResult, (error, csv) => {
                if (error) {
                    console.error('CSV conversion error:', error);
                    reject(error);
                } else {
                    console.log('CSV generated, size:', csv.length);
                    resolve(csv);
                }
            });
        });

        console.log('Initializing SES client');
        const ses = new sesClientModule.SESClient({
            region: process.env.AWS_REGION
        });
        const transporter = nodemailer.createTransport({
            SES: { ses, aws: sesClientModule }
        });

        console.log('Sending email');
        const info = await transporter.sendMail({
            from: process.env.sender,
            to: process.env.recipient,
            subject: subject,
            text: 'Please find the attached report.',
            attachments: [
                {
                    filename: `report_${reportTime}.csv`,
                    content: csv
                }
            ]
        });

        console.log('Email sent successfully');
        return `Report sent successfully: ${JSON.stringify(info)}`;
    } catch (error) {
        console.error('Error in handler:', error);
        console.error('Error stack:', error.stack);
        throw error;
    }
}

exports.handler = handler;
