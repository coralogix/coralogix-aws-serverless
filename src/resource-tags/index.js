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
    exportIntervalMillis: 100,
}));

['SIGINT', 'SIGTERM'].forEach(signal => {
    process.on(signal, () => meterProvider.shutdown().catch(console.error));
});

const meter = meterProvider.getMeter('example-exporter-collector');

const requestCounter = meter.createCounter('lambda_tags', {
    description: 'Example of a Counter',
});

function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {function} callback - Function callback
 */
function handler(event, context, callback) {
    diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);

    resourcegroupstaggingapi.getResources({
        ResourceTypeFilters: [
            "lambda",
        ],
    }).eachPage(function (err, data, done) {
        if (err) return callback(err);
        let resourcesCount = 0;
        if (data) {
            data.ResourceTagMappingList.forEach(function (resourceTagMapping) {
                const [resourceType, resourceId] = parseArn(resourceTagMapping.ResourceARN);
                
                let tags = formatTags(resourceTagMapping.Tags);
                tags["type"] = resourceType;
                tags["id"] = resourceId;

                console.debug(tags);
                
                requestCounter.add(0, tags);
                resourcesCount++;
            });

            meterProvider.forceFlush();
            
            console.info("Submitting " + resourcesCount + " resources");
        } else {
            return callback(null);
        };
    });
}

function formatTags(tagList) {
    var rv = {};
    tagList.map(function (tag) {
        let k = tag.Key;
        let v = tag.Value; 

        rv[k] = v;
    });
    return rv;
}

exports.handler = handler;

handler(null, null, a);

function a(err) {
    console.error("error " + err);
}