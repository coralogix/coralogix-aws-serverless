/**
 * AWS CloudWatch Metrics Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.4
 * @since       1.0.0
 */
 "use strict";

 // Import required libraries
const aws = require("aws-sdk");
const https = require("https");
const zlib = require("zlib");
const assert = require("assert");
const cloudwatch = new aws.CloudWatch();

// Check Lambda function parameters
const appName = process.env.app_name ? process.env.app_name : "NO_APPLICATION";
const coralogixUrl = process.env.CORALOGIX_URL || "api.coralogix.com";
assert(process.env.private_key, "No private key!");
assert(process.env.metrics, "No metrics list!");

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
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {function} callback - Function callback
 */
function handler (event, context, callback) {
    const EndTime = new Date;
    const StartTime = new Date(EndTime - 2 * 60 * 1000);

    try{
        JSON.parse(process.env.metrics).forEach((metric) => {
            cloudwatch.getMetricStatistics(Object.assign(metric, {
                "StartTime": StartTime,
                "EndTime": EndTime
            }), (error, result) => {
                if(error) {
                    callback(error);
                } else{
                    zlib.gzip(JSON.stringify(
                        result.Datapoints.map((datapoint) => ({
                            "applicationName": appName,
                            "subsystemName": metric.Namespace,
                            "timestamp": new Date(datapoint.Timestamp).getTime(),
                            "severity": 3,
                            "json": {
                                "Datapoint": datapoint,
                                "MetricName": metric.MetricName,
                                "Period": metric.Period,
                                "Dimensions": Object.fromEntries(
                                    metric.Dimensions.map((dimension) => [dimension.Name, dimension.Value])
                                )
                            }
                        })
                    )), (error, compressedEvents) => {
                        if (error) {
                            callback(error);
                        } else {
                            postToCoralogix(compressedEvents, callback);
                        }
                    });
                }
            });
        });
    } catch (error){
        callback(error);
    }
};

exports.handler = handler;
