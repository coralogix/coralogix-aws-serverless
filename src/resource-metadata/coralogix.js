import assert from 'assert'
import protoLoader from '@grpc/proto-loader'
import grpc from '@grpc/grpc-js'
import util from 'util';

const validateAndExtractConfiguration = () => {
    assert(process.env.PRIVATE_KEY, "No private key!")
    const privateKey = process.env.PRIVATE_KEY
    assert(process.env.CORALOGIX_METADATA_URL, "No Coralogix metadata URL key!")
    const coralogixMetadataUrl = process.env.CORALOGIX_METADATA_URL
    return { privateKey, coralogixMetadataUrl };
};
const { privateKey, coralogixMetadataUrl } = validateAndExtractConfiguration();

const metadataServiceDefinition = protoLoader.loadSync("service.proto", {
    includeDirs: ["proto"],
});
const metadataService = grpc.loadPackageDefinition(metadataServiceDefinition);

const createCredentials = () => {
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

export const sendToCoralogix = util.promisify(metadataClient.submit);
