/**
 * AWS Resource Tags Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     1.0.0
 * @since       1.0.0
 */

"use strict";

// Import required libraries
const aws = require("aws-sdk");
const assert = require("assert");
const resourcegroupstaggingapi = new aws.ResourceGroupsTaggingAPI();
const apigateway = new aws.APIGateway();
const protoLoader = require("@grpc/proto-loader");
const grpc = require("@grpc/grpc-js");
const parseArn = require("./resources").parseArn;
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-grpc');
const { MeterProvider, PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { Metadata } = require('@grpc/grpc-js');
const { MetricAttributes } = require('@opentelemetry/api');
const { diag, DiagConsoleLogger, DiagLogLevel } = require("@opentelemetry/api");

assert(process.env.private_key, "No private key!");
assert(process.env.coralogix_metrics_url, "No Coralogix endpoint!");

let global_tags = new Map();
let everything = [];

const metadata = new Metadata();
metadata.add('Authorization', 'Bearer ' + process.env.private_key);

const collectorOptions = {
    url: process.env.coralogix_metrics_url,
    metadata: metadata
};

const metricExporter = new OTLPMetricExporter(collectorOptions);

const meterProvider = new MeterProvider({
    resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'basic-metric-service',
    }),
});

meterProvider.addMetricReader(new PeriodicExportingMetricReader({
    exporter: metricExporter,
    exportIntervalMillis: 1000,
}));

async function init() {
    ['SIGINT', 'SIGTERM'].forEach(signal => {
        process.on(signal, () => meterProvider.shutdown().catch(console.error));
    });
    const meter = meterProvider.getMeter('example-exporter-collector');

    const gauge = meter.createObservableGauge("aws_tags_info");
    gauge.addCallback((observableResult) => {
        everything.forEach(element => {
            observableResult.observe(1, element);
        });
    });
}

function formatTags(tagList) {
    var rv = {};
    tagList.map(function (tag) {
        let k = "cxtag_" + tag.Key;
        let v = tag.Value; 

        rv[k] = v;
    });
    return rv;
}

async function handle_apigateway() {
    let position = null;

    do {
        const results = await apigateway.getRestApis({position: position}).promise();

        position = results.position;
        results.items.forEach(function (restapi) {
            global_tags.set("apigateway_" + restapi.id, restapi.name);
            console.debug("[apigateway] " + restapi.id + ": " + restapi.name);
        });
    } while (position !== undefined);
}

async function handle_tags() {
    let pages = 1;
    let resourcesCount = 0;

    let pagination_token = '';

    do {
        const results = await resourcegroupstaggingapi.getResources({
            ResourceTypeFilters: [
                "lambda",
                "apigateway"
            ],
            PaginationToken: pagination_token
        }).promise();

        pagination_token = results.PaginationToken;

        results.ResourceTagMappingList.forEach(function (resourceTagMapping) {
            const [resourceType, resourceId] = parseArn(resourceTagMapping.ResourceARN);
            
            let tags = formatTags(resourceTagMapping.Tags);
            tags["type"] = resourceType;
            if (resourceType.startsWith("aws:apigateway")) {
                let actual_name = global_tags.get("apigateway_" + resourceId);
                
                if (actual_name !== undefined) {
                    tags["ApiName"] = actual_name;
                }
            } else if (resourceType.startsWith("aws:lambda:function")) {
                tags["FunctionName"] = resourceId;
            }
            
            // Currently not supporting other tags
            // tags["id"] = resourceId;

            everything.push(tags);

            resourcesCount++;
        });

        meterProvider.forceFlush();
        
        console.info("Submitting " + resourcesCount + " resources");
    } while (pagination_token != '')
}

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {function} callback - Function callback
 */
async function handler(event, context, callback) {
    // diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.VERBOSE);
    console.debug("init");
    await init();

    console.debug("handle_apigateway");
    await handle_apigateway();

    console.debug("handle_tags");
    await handle_tags();
    
    await new Promise(resolve => setTimeout(resolve, 10000));

    meterProvider.shutdown();

    return callback(null);
}

exports.handler = handler;

// handler(null, null, a);

// console.debug("handler ended")

// function a(err) {
//     console.error("error " + err);
// }
