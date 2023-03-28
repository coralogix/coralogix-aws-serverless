exports.schemaUrl = ""

function extractArchitecture(architectures) {
    const aws_arch = architectures?.[0]

    return (aws_arch === 'x86_64')
        ? 'amd64'
        : (aws_arch === 'arm64')
            ? 'arm64'
            : ''
}

exports.extractArchitecture = extractArchitecture;

function intAttr(key, value) {
    return {
        key: key,
        value: {
            intValue: value,
        },
    }
}

exports.intAttr = intAttr;

function stringAttr(key, value) {
    return {
        key: key,
        value: {
            stringValue: value,
        },
    }
}

exports.stringAttr = stringAttr;

async function traverse(array, f) {
    return (await Promise.all(array.map(f)))
}

exports.traverse = traverse;