import assert from 'assert'
import { EC2Client, paginateDescribeInstances } from '@aws-sdk/client-ec2'


const validateAndExtractConfiguration = () => {
    assert(process.env.EC2_CHUNK_SIZE, "EC2_CHUNK_SIZE env var missing!")
    const chunkSize = parseInt(process.env.EC2_CHUNK_SIZE, 10)
    return { chunkSize };
};
const { chunkSize } = validateAndExtractConfiguration();

export const collectEc2Resources = async function* (region, clientConfig = {}) {
    console.info("Collecting list of EC2 instances");

    const ec2Client = new EC2Client({ region, ...clientConfig });
    for await (const page of paginateDescribeInstances({ client: ec2Client }, {})) {
        if (page.Reservations) {
            const pageInstances = page.Reservations.flatMap(r => r.Instances);

            for (let i = 0; i < pageInstances.length; i += chunkSize) {
                const chunk = pageInstances.slice(i, i + chunkSize);
                console.info(`Yielding chunk with ${chunk.length} instances`);
                yield chunk;
            }
        }
    }
}
