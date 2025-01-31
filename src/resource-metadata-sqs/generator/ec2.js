import assert from 'assert'
import { schemaUrl, stringAttr } from './common.js'

const validateAndExtractConfiguration = () => {
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!")
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10)
    return { resourceTtlMinutes };
};
const { resourceTtlMinutes } = validateAndExtractConfiguration();

export const generateEc2Resources = async (region, accountId, instances) => {

    console.info("Generating EC2 instances")
    const instanceResources = instances.map(i => makeEc2InstanceResource(i, region, accountId))

    instanceResources.forEach((f, index) =>
        console.debug(`Ec2Instance (${index + 1}/${instanceResources.length}): ${JSON.stringify(f)}`)
    )

    console.info(`Generated ${instanceResources.length} EC2 instances`)

    return instanceResources
}

const makeEc2InstanceResource = (i, region, accountId) => {
    // Handle both EC2 API and EventBridge property casing
    const instanceId = i.InstanceId || i.instanceId
    const arn = `arn:aws:ec2:${region}:${accountId}:instance/${instanceId}`

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_ec2"),
        stringAttr("cloud.account.id", accountId),
        stringAttr("cloud.region", region),
        stringAttr("cloud.availability_zone", i.Placement?.AvailabilityZone || i.placement?.availabilityZone),
        stringAttr("cloud.resource_id", arn),
        stringAttr("host.id", instanceId),
        stringAttr("host.image.id", i.ImageId || i.imageId),
        stringAttr("host.type", i.InstanceType || i.instanceType),
    ]

    // Handle tags in both formats
    const tags = i.Tags?.items || i.Tags || i.tagSet?.items || []
    const name = tags.find(kv => (kv.Key || kv.key) === "Name")?.Value || tags.find(kv => (kv.Key || kv.key) === "Name")?.value
    if (name) {
        attributes.push(stringAttr("host.name", name))
    }

    attributes.push(...convertEc2TagsToAttributes(tags))

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

// WARNING the tags data structure is different in lambda and in ec2
const convertEc2TagsToAttributes = tags => {
    if (!tags) {
        return []
    }
    return tags.map(tag => stringAttr(`cloud.tag.${tag.Key}`, tag.Value));
}
