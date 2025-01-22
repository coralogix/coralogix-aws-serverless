import { EC2Client, paginateDescribeInstances } from '@aws-sdk/client-ec2'

const ec2Client = new EC2Client();

export const collectEc2Resources = async () => {
    const instances = [];
    for await (const page of paginateDescribeInstances({ client: ec2Client }, {})) {
        if (page.Reservations) {
            instances.push(...page.Reservations.flatMap(r => r.Instances));
        }
    }
    return instances
}
