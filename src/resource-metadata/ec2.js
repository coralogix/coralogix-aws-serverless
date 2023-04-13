import assert from 'assert'
import { EC2Client, paginateDescribeInstances } from '@aws-sdk/client-ec2'
import { schemaUrl, stringAttr } from './common.js'

const validateAndExtractConfiguration = () => {
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!")
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10)
    return { resourceTtlMinutes };
};
const { resourceTtlMinutes } = validateAndExtractConfiguration();

const ec2Client = new EC2Client();

export const collectEc2Resources = async (region, accountId) => {

    console.info("Collecting EC2 instances")
    const instanceResources = await collectEc2InstanceResources(region, accountId)

    instanceResources.forEach(f =>
        console.debug(`Resource: ${JSON.stringify(f)}`)
    )

    console.debug(`Collected ${instanceResources.length} EC2 instances`)

    return instanceResources
}

const collectEc2InstanceResources = async (region, accountId) => {
    const instances = [];
    for await (const page of paginateDescribeInstances({ client: ec2Client }, {})) {
        if (page.Reservations) {
            instances.push(...page.Reservations.flatMap(r => r.Instances));
        }
    }
    return instances.map(i => makeEc2InstanceResource(i, region, accountId))
}

const makeEc2InstanceResource = (i, region, accountId) => {

    const instanceId = i.InstanceId
    const arn = `arn:aws:ec2:${region}:${accountId}:instance/${instanceId}`

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_ec2"),
        stringAttr("cloud.account.id", accountId),
        stringAttr("cloud.region", region),
        stringAttr("cloud.availability_zone", i.Placement?.AvailabilityZone),
        stringAttr("cloud.resource_id", arn),
        stringAttr("host.id", instanceId),
        stringAttr("host.image.id", i.ImageId),
        stringAttr("host.type", i.InstanceType),
    ]

    const name = i.Tags?.find(kv => kv.Key === "Name")?.Value
    if (name) {
        stringAttr("host.name", name)
    }

    if (i.Tags) {
        Object.keys(i.Tags).forEach(key => {
            attributes.push(stringAttr(`cloud.tag.${key}`, i.Tags[key]))
        })
    }

    return {
        resourceId: arn,
        resourceType: "aws:ec2:instance",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    }
}
