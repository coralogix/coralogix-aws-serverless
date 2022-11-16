function parseArn(resourceArn) {
    const arn = resourceArn.split(":");
    const partition = arn[1];
    const service = arn[2];
    if (arn.length > 6) {
        const resourceId = arn[6];
        const resourceType = partition + ":" + service + ":" + arn[5];
        return [resourceType, resourceId]
    } else {
        const resource = splitOnce(arn[5], "/");
        const resourceId = resource[1];
        const resourceType = partition + ":" + service + ":" + resource[0];
        return [resourceType, resourceId]
    }
}

function splitOnce(s, on) {
    const parts = s.split(on)
    return [parts[0], parts.length > 1 ? parts.slice(1).join(on) : null]
}

exports.parseArn = parseArn;
