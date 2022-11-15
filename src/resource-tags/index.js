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

// Check Lambda function parameters
assert(process.env.private_key, "No private key!");
assert(process.env.coralogix_metadata_url, "No Coralogix metadata URL key!");

// Load .proto definition
const metadataServiceDefinition = protoLoader.loadSync("service.proto");
const metadataService = grpc.loadPackageDefinition(metadataServiceDefinition);

function createCredentials(privateKey) {
    return grpc.credentials.combineChannelCredentials(
        grpc.credentials.createSsl(),
        grpc.credentials.createFromMetadataGenerator(function (options, callback) {
            const metadata = new grpc.Metadata();
            metadata.set('authorization', 'Bearer ' + privateKey);
            return callback(null, metadata);
        })
    );
}

const credentials = createCredentials(process.env.private_key);
const metadataClient = new metadataService.com.coralogix.metadata.gateway.v1.MetadataGatewayService(
    process.env.coralogix_metadata_url,
    credentials
);

/**
 * @description Lambda function handler
 * @param {object} event - Event data
 * @param {object} context - Function context
 * @param {function} callback - Function callback
 */
function handler(event, context, callback) {
    resourcegroupstaggingapi.getResources({
        // The current API can only accept resources with globally unique IDs
        ResourceTypeFilters: [
            "ec2:instance",
        ],
    }).eachPage(function (err, data, done) {
        if (err) return callback(err);
        if (data) {
            const resources = [];
            data.ResourceTagMappingList.forEach(function (resourceTagMapping) {
                const [resourceType, resourceId] = parseArn(resourceTagMapping.ResourceARN);
                resources.push({
                    resourceId,
                    resourceType,
                    tags: formatTags(resourceTagMapping.Tags)
                });
            });
            console.info("Submitting " + resources.length + " resources");
            metadataClient.submit({ resources }, function (err, result) {
                if (err) return callback(err);
                done();
            });
        } else {
            return callback(null);
        };
    });
}

function formatTags(tagList) {
    return tagList.map(function (tag) {
        return ({ key: tag.Key, value: tag.Value });
    });
}

exports.handler = handler;
