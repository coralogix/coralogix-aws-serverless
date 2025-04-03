export const schemaUrl = "";

export const extractArchitecture = architectures => {
    const awsArchitecture = architectures?.[0];
    switch (awsArchitecture) {
        case 'x86_64':
            return 'amd64';
        case 'arm64':
            return 'arm64';
        default:
            return '';
    }
};

export const intAttr = (key, value) => ({
    key: key,
    value: {
        intValue: value,
    },
});

export const stringAttr = (key, value) => ({
    key: key,
    value: {
        stringValue: value,
    },
});

export const traverse = async (array, f) => {
    const results = [];
    for (var i = 0; i < array.length; i++) {
        results.push(await f(array[i], i));
    }
    return results;
};

export const flatTraverse = async (array, f) => {
    const results = [];
    for (var i = 0; i < array.length; i++) {
        let result = await f(array[i], i);
        if (result) {
            results.push(result);
        }
    }
    return results;
};
