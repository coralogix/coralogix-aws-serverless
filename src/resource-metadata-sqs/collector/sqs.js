import assert from 'assert'
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs'

const validateAndExtractConfiguration = () => {
    assert(process.env.METADATA_QUEUE_URL, "METADATA_QUEUE_URL env var missing!")
    return { queueUrl: process.env.METADATA_QUEUE_URL };
};

const { queueUrl } = validateAndExtractConfiguration();

const sqsClient = new SQSClient();

export const sendToSqs = async ({ source, region, resources }) => {
    const message = {
        source,
        region,
        resources,
        timestamp: new Date().toISOString()
    };

    const command = new SendMessageCommand({
        QueueUrl: queueUrl,
        MessageBody: JSON.stringify(message)
    });

    await sqsClient.send(command);
};
