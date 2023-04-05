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

export const traverse = async (array, f) =>
    await Promise.all(array.map(f))
