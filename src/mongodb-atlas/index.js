/**
 * MongoDB Atlas Lambda function for Coralogix
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
const assert = require("assert");
const https = require("https");
const crypto = require("crypto");
const querystring = require("querystring");
const zlib = require("zlib");
const coralogix = require("coralogix-logger");
const lambda = new aws.Lambda();

// Check Lambda function parameters
assert(process.env.CORALOGIX_PRIVATE_KEY, "No Coralogix Private Key!");
assert(process.env.MONGODB_ATLAS_PUBLIC_API_KEY, "MongoDB Atlas Public API key is not set");
assert(process.env.MONGODB_ATLAS_PRIVATE_API_KEY, "MongoDB Atlas Private API key is not set");
assert(process.env.MONGODB_ATLAS_PROJECT_NAME, "MongoDB Atlas Project name is not set");
assert(process.env.MONGODB_ATLAS_RESOURCES, "MongoDB Atlas resources list is not set");

// Initialize new Coralogix logger
coralogix.CoralogixCentralLogger.configure(new coralogix.LoggerConfig({
    privateKey: process.env.CORALOGIX_PRIVATE_KEY
}));
const logger = new coralogix.CoralogixCentralLogger();

/**
 * @description Authorizes to MongoDB Atlas API
 * @param {string} path - The API request path
 * @returns {Promise} Authorization token
 */
function mongoAuth(path) {
    return new Promise((resolve, reject) => {
        https.get({
            host: "cloud.mongodb.com",
            path: path,
            timeout: 10000
        }, (response) => {
            if (!response.headers.hasOwnProperty("www-authenticate")) {
                reject(new Error("Authorization failed"));
            }
            const username = process.env.MONGODB_ATLAS_PUBLIC_API_KEY;
            const password = process.env.MONGODB_ATLAS_PRIVATE_API_KEY;
            const nc = "00000001";
            const cnonce = crypto.randomBytes(32).toString("base64");
            let authorization = querystring.parse(
                response.headers["www-authenticate"].replace(/^Digest\s*/, "").replace(/\+/g, "%2B"),
                ", ",
                "=",
                { decodeURIComponent: str => querystring.unescape(str.replace(/\"/g, "")) }
            );
            Object.assign(authorization, {
                username: username,
                uri: path,
                cnonce: cnonce,
                nc: nc,
                response: crypto.createHash("md5").update([
                    crypto.createHash("md5").update(`${username}:${authorization.realm}:${password}`).digest("hex"),
                    authorization.nonce,
                    nc,
                    cnonce,
                    authorization.qop,
                    crypto.createHash("md5").update(`GET:${path}`).digest("hex")
                ].join(":")).digest("hex")
            });
            delete authorization.domain;
            delete authorization.stale;
            resolve(
                "Digest " + querystring.stringify(
                    authorization,
                    ", ",
                    "=",
                    { encodeURIComponent: str => Object.keys(authorization).includes(str) || ["MD5", "auth", nc].includes(str) ? str : `"${str}"` }
                )
            );
        }).on("error", reject);
    });
}

/**
 * @description Sends request to MongoDB Atlas API
 * @param {string} path - The API request path
 * @returns {Promise} API response
 */
function mongoApi(path, query = null) {
    return new Promise((resolve, reject) => {
        if (query !== null) path += "?" + querystring.stringify(query);
        mongoAuth(path).then((authorization) => {
            https.get({
                host: "cloud.mongodb.com",
                path: `${path}?${querystring.stringify(query)}`,
                headers: {
                    "Accept": "application/json",
                    "Authorization": authorization
                },
                timeout: 10000
            }, (response) => {
                let body = [];
                if (response.statusCode != 200) {
                    reject(new Error(`Request to ${path} failed: ${response.statusCode}`));
                }
                response.setEncoding("utf8");
                response.on("data", (chunk) => body.push(chunk));
                response.on("end", () => resolve(JSON.parse(body.join(""))));
            }).on("error", reject);
        }).catch(reject);
    });
}

/**
 * @description Retrieves a log file that contains a range of log messages for a particular host
 * @param {string} group_id - Project identifier
 * @param {string} hostname - Name of the host where the log files are stored
 * @param {string} log_name - The name of the log file that you want to retrieve
 * @param {object} log_range - Timestamps that specify starting and end points for the range of log messages to retrieve
 * @returns {Promise} Log lines
 */
function mongoLogs(group_id, hostname, log_name, log_range) {
    const allowed_log_names = [
        "mongodb",
        "mongodb-audit-log",
        "mongos",
        "mongos-audit-log"
    ];
    return new Promise((resolve, reject) => {
        if (!allowed_log_names.includes(log_name)) {
            reject(`Unsupported log name: ${log_name}`);
        }
        const path = `/api/atlas/v1.0/groups/${group_id}/clusters/${hostname}/logs/${log_name}.gz?${querystring.stringify(log_range)}`;
        mongoAuth(path).then((authorization) => {
            https.get({
                host: "cloud.mongodb.com",
                path: path,
                headers: {
                    "Accept": "application/gzip",
                    "Authorization": authorization
                },
                timeout: 120000
            }, (response) => {
                let body = [];
                if (response.statusCode != 200) {
                    reject(new Error(`Request to /logs/${log_name}.gz failed: ${response.statusCode}`));
                }
                if (response.headers["content-length"] === undefined || parseInt(response.headers["content-length"], 10) > 0) {
                    let gunzip = zlib.createGunzip();
                    response.pipe(gunzip);
                    gunzip.on("data", (chunk) => body.push(chunk));
                    gunzip.on("end", () => resolve(body.join("").split(/(?:\r\n|\r|\n)/g)));
                } else {
                    resolve([]);
                }
            }).on("error", reject);
        }).catch(reject);
    });
}

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {object} callback - Function callback
 */
function handler(event, context, callback) {
    lambda.getFunction({
        FunctionName: context.functionName
    }, (error, func) => {
        if (!error) {
            mongoApi(`/api/atlas/v1.0/groups/byName/${process.env.MONGODB_ATLAS_PROJECT_NAME}`).then((project) => {
                process.env.MONGODB_ATLAS_RESOURCES.split(",").forEach((resource) => {
                    switch(resource) {
                        case "mongodb":
                        case "mongodb-audit-log":
                        case "mongos":
                        case "mongos-audit-log":
                            assert(process.env.MONGODB_ATLAS_CLUSTER_NAME, "MongoDB Atlas Cluster name is not set");
                            mongoApi(`/api/atlas/v1.0/groups/${project.id}/clusters/${process.env.MONGODB_ATLAS_CLUSTER_NAME}`).then((cluster) => {
                                cluster.mongoURI.replace(/^mongodb:\/\//, "").split(",").map((host) => host.split(":")).forEach(([hostname, port]) => {
                                    const range = {
                                        startDate: func.Tags[`${hostname}_${resource}`] || Math.round(Date.now() / 1000) - 300,
                                        endDate: Math.round(Date.now() / 1000)
                                    };
                                    mongoLogs(
                                        project.id,
                                        hostname,
                                        resource,
                                        range
                                    ).then((logs) => {
                                        console.log(`Logs [${hostname}][${resource}]:`, logs.length);
                                        logs.forEach((log) => {
                                            if (log) {
                                                logger.addLogWithHostname(
                                                    process.env.CORALOGIX_APP_NAME || project.name,
                                                    process.env.CORALOGIX_SUB_SYSTEM || cluster.name,
                                                    hostname,
                                                    new coralogix.Log({
                                                        severity: coralogix.Severity.info,
                                                        text: log,
                                                        category: resource,
                                                        threadId: cluster.id
                                                    })
                                                );
                                            }
                                        });
                                        if (logs.length > 0) {
                                            lambda.tagResource({
                                                Resource: func.Configuration.FunctionArn,
                                                Tags: {
                                                    [`${hostname}_${resource}`]: range.endDate.toString()
                                                }
                                            }, (error, data) => {
                                                if (error) {
                                                    callback(error);
                                                }
                                            });
                                        }
                                    }).catch(callback);
                                });
                            }).catch(callback);
                            break;
                        case "metrics":
                            assert(process.env.MONGODB_ATLAS_CLUSTER_NAME, "MongoDB Atlas Cluster name is not set");
                            mongoApi(`/api/atlas/v1.0/groups/${project.id}/clusters/${process.env.MONGODB_ATLAS_CLUSTER_NAME}`).then((cluster) => {
                                cluster.mongoURI.replace(/^mongodb:\/\//, "").split(",").map((host) => host.split(":")).forEach(([hostname, port]) => {
                                    const start = new Date();
                                    const end = new Date();
                                    start.setMinutes(start.getMinutes() - 5);
                                    mongoApi(`/api/atlas/v1.0/groups/${project.id}/processes/${hostname}:${port}/measurements`, {
                                        granularity: process.env.MONGODB_ATLAS_METRICS_GRANULARITY || "PT5M",
                                        start: func.Tags[`${hostname}_metrics`] || start.toISOString(),
                                        end: end.toISOString(),
                                        itemsPerPage: 500
                                    }).then((metrics) => {
                                        console.log(`Metrics [${hostname}]:`, metrics.measurements.length);
                                        metrics.measurements.forEach((metric) => {
                                            logger.addLogWithHostname(
                                                process.env.CORALOGIX_APP_NAME || project.name,
                                                process.env.CORALOGIX_SUB_SYSTEM || cluster.name,
                                                hostname,
                                                new coralogix.Log({
                                                    severity: coralogix.Severity.info,
                                                    text: JSON.stringify(metric),
                                                    category: "metrics",
                                                    threadId: cluster.id
                                                })
                                            );
                                        });
                                        if (metrics.length > 0) {
                                            lambda.tagResource({
                                                Resource: func.Configuration.FunctionArn,
                                                Tags: {
                                                    [`${hostname}_metrics`]: end.toISOString()
                                                }
                                            }, (error, data) => {
                                                if (error) {
                                                    callback(error);
                                                }
                                            });
                                        }
                                    }).catch(callback);
                                });
                            }).catch(callback);
                            break;
                        case "events":
                            const minDate = new Date();
                            const maxDate = new Date();
                            minDate.setMinutes(minDate.getMinutes() - 5);
                            mongoApi(`/api/atlas/v1.0/groups/${project.id}/events`, {
                                minDate: func.Tags["events"] || minDate.toISOString(),
                                maxDate: maxDate.toISOString(),
                                itemsPerPage: 500
                            }).then((events) => {
                                console.log(`Events [${project.name}]:`, events.totalCount);
                                events.results.forEach((event) => {
                                    logger.addLog(
                                        process.env.CORALOGIX_APP_NAME || project.name,
                                        process.env.CORALOGIX_SUB_SYSTEM || "events",
                                        new coralogix.Log({
                                            severity: coralogix.Severity.info,
                                            text: JSON.stringify(event),
                                            category: "events",
                                            threadId: project.id
                                        })
                                    );
                                });
                                if (events.results.length > 0) {
                                    lambda.tagResource({
                                        Resource: func.Configuration.FunctionArn,
                                        Tags: {
                                            "events": maxDate.toISOString()
                                        }
                                    }, (error, data) => {
                                        if (error) {
                                            callback(error);
                                        }
                                    });
                                }
                            }).catch(callback);
                            break;
                        case "alerts":
                            mongoApi(`/api/atlas/v1.0/groups/${project.id}/alerts`, {
                                status: "OPEN",
                                itemsPerPage: 500
                            }).then((alerts) => {
                                console.log(`Alerts [${project.name}]:`, alerts.totalCount);
                                alerts.results.forEach((alert) => {
                                    logger.addLog(
                                        process.env.CORALOGIX_APP_NAME || project.name,
                                        process.env.CORALOGIX_SUB_SYSTEM || "alerts",
                                        new coralogix.Log({
                                            severity: coralogix.Severity.info,
                                            text: JSON.stringify(alert),
                                            category: "alerts",
                                            threadId: project.id
                                        })
                                    );
                                });
                            }).catch(callback);
                            break;
                        default:
                            console.log("Unsupported resource type:", resource);
                            break;
                    }
                });
            }).catch(callback);
        } else {
            callback(error);
        }
    });
}

exports.handler = handler;
