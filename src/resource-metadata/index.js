/**
 * AWS Resource Tags Lambda function for Coralogix
 *
 * @file        This file is lambda function source code
 * @author      Coralogix Ltd. <info@coralogix.com>
 * @link        https://coralogix.com/
 * @copyright   Coralogix Ltd.
 * @licence     Apache-2.0
 * @version     0.1.0
 * @since       0.1.0
 */

"use strict";

const assert = require("assert");
const protoLoader = require("@grpc/proto-loader");
const grpc = require("@grpc/grpc-js");
const util = require('util');

const { collectLambdaResources } = require("./lambda.js")
const { collectEc2Resources } = require("./ec2.js")

// Check Lambda function parameters
assert(process.env.PRIVATE_KEY, "No private key!")
const privateKey = process.env.PRIVATE_KEY
assert(process.env.CORALOGIX_METADATA_URL, "No Coralogix metadata URL key!")
const coralogixMetadataUrl = process.env.CORALOGIX_METADATA_URL

// Load .proto definition
const metadataServiceDefinition = protoLoader.loadSync("service.proto", {
    includeDirs: ["proto"],
});
const metadataService = grpc.loadPackageDefinition(metadataServiceDefinition);

function createCredentials() {
    return grpc.credentials.combineChannelCredentials(
        grpc.credentials.createSsl(),
        grpc.credentials.createFromMetadataGenerator(function (options, callback) {
            const metadata = new grpc.Metadata();
            metadata.set('authorization', 'Bearer ' + privateKey);
            return callback(null, metadata);
        })
    );
}

const credentials = createCredentials();
const metadataClient = new metadataService.com.coralogix.metadata.gateway.v2.MetadataGatewayService(
    coralogixMetadataUrl,
    credentials
);
metadataClient.submit[util.promisify.custom] = (input) => {
    return new Promise((resolve, reject) => {
        metadataClient.submit(input, function (err, response) {
            if (err) {
                reject(err)
            } else {
                resolve(response)
            }
        });
    });
};
const sendToCoralogix = util.promisify(metadataClient.submit);


/**
 * @description Lambda function handler
 */
async function handler() {
    const collectorId = "resource-metadata"

    console.info("Collecting Lambda resources")
    const lambdaResources = await collectLambdaResources()
    console.info("Sending Lambda resources to coralogix")
    await sendToCoralogix({
        collectorId,
        resources: lambdaResources,
    })

    console.info("Collecting EC2 resources")
    const ec2Resources = await collectEc2Resources()
    console.info("Sending EC2 resources to coralogix")
    await sendToCoralogix({
        collectorId,
        resources: ec2Resources,
    })
}

exports.handler = handler;
