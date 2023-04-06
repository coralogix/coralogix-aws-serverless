export const schemaUrl = ""

export const extractArchitecture = architectures => {
    const awsArchitecture = architectures?.[0]
    switch (awsArchitecture) {
        case 'x86_64':
            return 'amd64'
        case 'arm64':
            return 'arm64'
        default:
            return ''
    }
}

export const intAttr = (key, value) => ({
    key: key,
    value: {
        intValue: value,
    },
})

export const stringAttr = (key, value) => ({
    key: key,
    value: {
        stringValue: value,
    },
})

export const traverse = async (array, f) => {
    const results = [];
    for (const a of array) {
        results.push(await f(a));
    }
    return results;
}