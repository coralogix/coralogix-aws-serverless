import { EC2Client, paginateDescribeInstances } from '@aws-sdk/client-ec2'

const ec2Client = new EC2Client();

export const collectEc2Resources = async function* () {
    console.info("Collecting list of EC2 instances");
    const CHUNK_SIZE = 25;

    for await (const page of paginateDescribeInstances({ client: ec2Client }, {})) {
        if (page.Reservations) {
            const pageInstances = page.Reservations.flatMap(r => r.Instances);

            // Chunk the instances array into groups of CHUNK_SIZE to avoid exceeding the SQS message size limit
            for (let i = 0; i < pageInstances.length; i += CHUNK_SIZE) {
                const chunk = pageInstances.slice(i, i + CHUNK_SIZE);
                console.info(`Yielding chunk with ${chunk.length} instances`);
                yield chunk;
            }
        }
    }
}
