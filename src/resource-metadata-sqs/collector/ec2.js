import { EC2Client, paginateDescribeInstances } from '@aws-sdk/client-ec2'

const ec2Client = new EC2Client();

export const collectEc2Resources = async function* () {
    for await (const page of paginateDescribeInstances({ client: ec2Client }, { MaxItems: 5 })) {
        if (page.Reservations) {
            const pageInstances = page.Reservations.flatMap(r => r.Instances);
            if (pageInstances.length > 0) {
                yield pageInstances;
            }
        }
    }
}
