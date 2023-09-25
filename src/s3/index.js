"use strict";

const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const client = new S3Client({});
const zlib = require("zlib");
const assert = require("assert");
const https = require("https");
const microtime = require("microtime");
const util = require('util');
const eventStream = require('event-stream');
const { PassThrough } = require('stream');
const gzip = util.promisify(zlib.gzip);

assert(process.env.private_key, "No private key!");

const newlinePattern = process.env.newline_pattern ? RegExp(process.env.newline_pattern) : /(?:\r\n|\r|\n)/g;
const blockingPattern = process.env.blocking_pattern ? RegExp(process.env.blocking_pattern) : null;
const sampling = process.env.sampling ? parseInt(process.env.sampling) : 1;
const coralogixUrl = process.env.CORALOGIX_URL || "ingress.coralogix.com";

async function postToCoralogix(logs, retryNumber = 0, retryLimit = 3) {
    return new Promise((resolve, reject) => {
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

function dig(path, object) {
    if (path.startsWith("$.")) {
        return path.split(".").slice(1).reduce((xs, x) => (xs && xs[x]) ? xs[x] : path, object);
    }
    return path;
}

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

async function handler(event, context, callback) {
    const bucket_name = event.Records[0].s3.bucket.name;
    const key_name = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, " "));
    const file_size = event.Records[0].s3.object.size;

    if (file_size === 0) {
        console.log("Skipping empty file:", key_name);
        return callback(null, "Skip empty file");
    }

    const params = {
        Bucket: bucket_name,
        Key: key_name,
    };

    const command = new GetObjectCommand(params);
    const response = await client.send(command);
    const s3Stream = response.Body;

    let appName = process.env.app_name || "NO_APPLICATION";
    let subName = process.env.sub_name || "NO_SUBSYSTEM";
    let sampledEvents = [];

    const gunzip = zlib.createGunzip();
    const outStream = new PassThrough();

    s3Stream
        .pipe(gunzip)
        .pipe(outStream)
        .pipe(eventStream.split())
        .pipe(eventStream.mapSync(async (line) => {
            if (blockingPattern && line.match(blockingPattern)) return;

            try {
                appName = appName.startsWith("$.") ? dig(appName, JSON.parse(line)) : appName;
                subName = subName.startsWith("$.") ? dig(subName, JSON.parse(line)) : subName;
            } catch {}

            sampledEvents.push({
                "applicationName": appName,
                "subsystemName": subName,
                "timestamp": microtime.now(),
                "severity": getSeverityLevel(line.toLowerCase()),
                "text": line,
                "threadId": ""
            });
            console.log(sampledEvents);
            if (sampledEvents.length >= 100) {
                const compressedBody = await gzip(JSON.stringify(sampledEvents));
                await postToCoralogix(compressedBody);
                sampledEvents = [];
            }
        }))
        .on('end', async () => {
            if (sampledEvents.length > 0) {
                const compressedBody = await gzip(JSON.stringify(sampledEvents));
                await postToCoralogix(compressedBody);
            }
        })
        .on('error', (err) => {
            console.error('Error while processing the stream: ', err);
        });
}

exports.handler = handler;
