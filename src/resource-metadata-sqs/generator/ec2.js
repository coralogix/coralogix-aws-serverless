import assert from 'assert';
import { schemaUrl, stringAttr } from './common.js';
import { EC2Client, DescribeInstancesCommand } from "@aws-sdk/client-ec2";
import { assumeRole, getAccountId } from './crossaccount.js';

const validateAndExtractConfiguration = () => {
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!");
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10);
    const roleName = process.env.CROSSACCOUNT_IAM_ROLE_NAME ? process.env.CROSSACCOUNT_IAM_ROLE_NAME : "CrossAccountEC2Role";
    return { resourceTtlMinutes, roleName };
};
const { resourceTtlMinutes, roleName } = validateAndExtractConfiguration();

export const generateEc2Resources = async (region, accountId, instances, mode = "api") => {
    let instancesArray = [];

    // If mode is "config", fetch detailed information using DescribeInstances
    if (mode === "config") {
        // Extract instance IDs from the resources array
        const instanceIds = instances.map(resource => resource.ResourceId);
        console.log(`Fetching details for ${instanceIds.length} EC2 instances in ${region} using AWS EC2 API`);

        // Create EC2 client with appropriate credentials
        const currentAccountId = await getAccountId();
        let ec2Client;

        if (accountId === currentAccountId) {
            // Create normal EC2Client for the current account
            ec2Client = new EC2Client({ region });
        } else {
            const roleArn = `arn:aws:iam::${accountId}:role/${roleName}`;

            // Assume role and create EC2Client with assumed credentials
            const credentials = await assumeRole(roleArn);
            ec2Client = new EC2Client({ region, credentials });
        }
        // Fetch detailed instance information
        console.log(instanceIds)
        const command = new DescribeInstancesCommand({
            InstanceIds: instanceIds
        });

        const response = await ec2Client.send(command);

        // DescribeInstances returns data in a nested Reservations > Instances structure
        for (const reservation of response.Reservations || []) {
            for (const instance of reservation.Instances || []) {
                instancesArray.push(instance);
            }
        }

        console.log(`Successfully retrieved details for ${instancesArray.length} EC2 instances`);
    }
    else {
        instancesArray = instances;
    }

    console.log(`Processing ${instancesArray.length} EC2 instances in ${region}`);
    const instanceResources = instancesArray.map(i => makeEc2InstanceResource(i, region, accountId));

    instanceResources.forEach((f, index) =>
        console.debug(`Ec2Instance (${index + 1}/${instanceResources.length}): ${JSON.stringify(f)}`)
    );

    console.info(`Generated ${instanceResources.length} EC2 instances`);

    return instanceResources;
};

const makeEc2InstanceResource = (i, region, accountId) => {
    // Handle both EC2 API and EventBridge property casing
    const instanceId = i.InstanceId || i.instanceId;
    const arn = `arn:aws:ec2:${region}:${accountId}:instance/${instanceId}`;

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
    ];

    // Handle tags in both formats
    const tags = i.Tags?.items || i.Tags || i.tagSet?.items || [];
    const name = tags.find(kv => (kv.Key || kv.key) === "Name")?.Value || tags.find(kv => (kv.Key || kv.key) === "Name")?.value;
    if (name) {
        attributes.push(stringAttr("host.name", name));
    }

    attributes.push(...convertEc2TagsToAttributes(tags));

    return {
        resourceId: arn,
        resourceType: "aws:ec2:instance",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    };
};

// WARNING the tags data structure is different in lambda and in ec2
const convertEc2TagsToAttributes = tags => {
    if (!tags) {
        return [];
    }
    return tags.map(tag => stringAttr(`cloud.tag.${tag.Key}`, tag.Value));
};
