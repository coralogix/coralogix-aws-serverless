/**
 * AWS S3 Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.28
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const client = new S3Client({});
const zlib = require("zlib");
const assert = require("assert");
const https = require("https");
var microtime = require("microtime")
const util = require('util');
const gzip = util.promisify(zlib.gzip);
const stream = require('stream');
const { promisify } = require('util');

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
const newlinePattern = process.env.newline_pattern ? RegExp(process.env.newline_pattern) : /(?:\r\n|\r|\n)/g;
const blockingPattern = process.env.blocking_pattern ? RegExp(process.env.blocking_pattern) : null;
const sampling = process.env.sampling ? parseInt(process.env.sampling) : 1;
const coralogixUrl = process.env.CORALOGIX_URL || "ingress.coralogix.com";
const debug = JSON.parse(process.env.debug || false);
const sampledEvents = [];
/**
 * @description Send logs records to Coralogix
 * @param {Buffer} content - Logs records data
 * @param {string} filename - Logs filename S3 path
 */
const pipeline = promisify(stream.pipeline);

async function gunzipStream(inputStream) {
  const gunzip = zlib.createGunzip();
  const chunks = [];
  const outputStream = new stream.Writable({
    write(chunk, _, callback) {
      chunks.push(chunk);
      callback();
    }
  });
  await pipeline(inputStream, gunzip, outputStream);
  return Buffer.concat(chunks).toString('utf-8');
}

function postToCoralogix(logs, retryNumber = 0, retryLimit = 3) {
    return new Promise((resolve, reject) => {
        let responseBody = "";
        try {
            const request = https.request({
                hostname: coralogixUrl,
                port: 443,
                path: "/logs/rest/singles",
                //path: "/fastly",
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
                response.setEncoding("utf8");
                response.on("data", (chunk) => responseBody += chunk);
                response.on("end", () => {
                    if (response.statusCode != 200) reject(new Error(responseBody));
                    resolve(responseBody);
                });
            });

            request.on("timeout", () => {
                request.destroy();
                if (++retryNumber < retryLimit) {
                    postToCoralogix(logs, retryNumber, retryLimit)
                        .then(resolve)
                        .catch(reject);
                } else {
                    reject(new Error("Failed all retries"));
                }
            });

            request.on("error", reject);
            request.write(logs);
            request.end();
        } catch (error) {
            reject(error);
        }
    });
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
const readFile = async (bucket, key) => {
    const params = {
        Bucket: bucket,
        Key: key,
        };

    const command = new GetObjectCommand(params);
    const response = await client.send(command);

    const { Body } = response; 
    if (key.endsWith('.gz')) {
    return await gunzipStream(Body);
    } else {
    return streamToString(Body);
  }
};;
    
const streamToString = (stream) => new Promise((resolve, reject) => {
    const chunks = [];
    stream.on('data', (chunk) => chunks.push(chunk));
    stream.on('error', reject);
    stream.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
});

async function handler(event, context, callback) { 
    const bucket_name = event.Records[0].s3.bucket.name;
    const key_name = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, " "));
    const file_size = event.Records[0].s3.object.size;

  // Skip processing for empty files
    if (file_size === 0) {
        console.log("Skipping empty file:", key_name);
        return callback(null, "Skip empty file");
    }

    const content = await readFile(bucket_name, key_name);

    const parsedEvents = content.split(newlinePattern);
    let appName = process.env.app_name || "NO_APPLICATION";
    let subName = process.env.sub_name || "NO_SUBSYSTEM";

    try {
        appName = appName.startsWith("$.") ? dig(appName, JSON.parse(parsedEvents)) : appName;
        subName = subName.startsWith("$.") ? dig(subName, JSON.parse(parsedEvents)) : subName;
    } catch {}
    
    for (let i = 0; i < parsedEvents.length; i += sampling) {
        if (!parsedEvents[i]) continue;
        if (blockingPattern && parsedEvents[i].match(blockingPattern)) continue;
        let appName = process.env.app_name || "NO_APPLICATION";
        let subName = process.env.sub_name || "NO_SUBSYSTEM";

        try {
            appName = appName.startsWith("$.") ? dig(appName, JSON.parse(parsedEvents[i])) : appName;
            subName = subName.startsWith("$.") ? dig(subName, JSON.parse(parsedEvents[i])) : subName;
        } catch {}
        sampledEvents.push(parsedEvents[i]);
        
    }
    const lala = sampledEvents.map((eventRecord) => {
            return {
            "applicationName": appName,
            "subsystemName": subName,
            "timestamp": microtime.now(),
            "severity": getSeverityLevel(eventRecord.toLowerCase()),
            "text": eventRecord,
            "threadId": ""};
    });
    const compressedBody = await gzip(JSON.stringify(lala));
    return await postToCoralogix(compressedBody, callback);
    

}

exports.handler = handler;