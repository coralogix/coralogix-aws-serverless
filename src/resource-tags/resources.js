function parseArn(resourceArn) {
    const arn = resourceArn.split(":");
    const partition = arn[1];
    const service = arn[2];
    const region = arn[3];
    const account_id = arn[4];

    if (arn.length > 6) {
        const resourceId = arn[6];
        const resourceType = partition + ":" + service + ":" + arn[5];
        return [account_id, region, resourceType, resourceId]
    } else if (service === "apigateway") {
        const resource = arn[5].split("/");
        return [account_id, region, partition + ":" + service + ":" + resource[1], resource[2]];
    } else {
        const resource = splitOnce(arn[5], "/");
        const resourceId = resource[1];
        const resourceType = partition + ":" + service + ":" + resource[0];
        return [account_id, region, resourceType, resourceId]
    }
}

function splitOnce(s, on) {
    const parts = s.split(on)
    return [parts[0], parts.length > 1 ? parts.slice(1).join(on) : null]
}

exports.parseArn = parseArn;
