import assert from 'assert'
import { LambdaClient, GetFunctionCommand, ListAliasesCommand, GetPolicyCommand, ListVersionsByFunctionCommand, ListEventSourceMappingsCommand } from '@aws-sdk/client-lambda'
import { schemaUrl, extractArchitecture, intAttr, stringAttr, traverse, flatTraverse } from './common.js'

const validateAndExtractConfiguration = () => {
    assert(process.env.LATEST_VERSIONS_PER_FUNCTION, "LATEST_VERSIONS_PER_FUNCTION env var missing!")
    const latestVersionsPerFunction = parseInt(process.env.LATEST_VERSIONS_PER_FUNCTION, 10)
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!")
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10)
    assert(process.env.COLLECT_ALIASES, "COLLECT_ALIASES env var missing!")
    const collectAliases = String(process.env.COLLECT_ALIASES).toLowerCase() === "true"
    return { latestVersionsPerFunction, resourceTtlMinutes, collectAliases };
}
const { latestVersionsPerFunction, resourceTtlMinutes, collectAliases } = validateAndExtractConfiguration();

const lambdaClient = new LambdaClient();

// Helper function to normalize property access regardless of case
const prop = (obj, key) => {
    const upperKey = key.charAt(0).toUpperCase() + key.slice(1);
    const lowerKey = key.charAt(0).toLowerCase() + key.slice(1);
    return obj[upperKey] ?? obj[lowerKey];
}

export const generateLambdaResources = async (functions) => {
    // Normalize function objects to handle both cases
    functions = functions.map(f => ({
        functionArn: prop(f, 'functionArn'),
        functionName: prop(f, 'functionName'),
        ...f
    }));

    console.info("Generating function details")
    const { functionResources, aliasResources, versionsToCollect } = await generateFunctionAndAliasResources(functions)

    console.info("Generating function version details")
    const functionVersionResources = await generateFunctionVersionResources(versionsToCollect)

    const resources = [...functionResources, ...functionVersionResources, ...aliasResources]

    console.info(`Generated ${functionResources.length} functions, ${functionVersionResources.length} function versions and ${aliasResources.length} aliases`)

    return resources
}

const generateFunctionAndAliasResources = async (listOfFunctions) => {
    const results = await flatTraverse(listOfFunctions, async (lambdaFunctionVersionLatest, index) => {
        const functionName = prop(lambdaFunctionVersionLatest, 'functionName')
        try {
            const lambdaFunction = await lambdaClient.send(new GetFunctionCommand({ FunctionName: functionName }))
            const functionResource = makeLambdaFunctionResource(lambdaFunction)

            const aliases = collectAliases
                ? (await lambdaClient.send(new ListAliasesCommand({ FunctionName: functionName })))?.Aliases
                : []
            const aliasResources = aliases.map(alias => makeAliasResource(functionName, alias))

            const versions = latestVersionsPerFunction > 0
                ? (await lambdaClient.send(new ListVersionsByFunctionCommand({ FunctionName: functionName }))).Versions
                : [lambdaFunctionVersionLatest]

            const versionsToCollect = versions.filter((version, index) => {
                return (index <= latestVersionsPerFunction)
                    || (aliases.some(alias => prop(version, 'version') === alias.FunctionVersion))
            })

            console.debug(`Function (${index + 1}/${listOfFunctions.length}): ${JSON.stringify(functionResource)}`)
            aliasResources.forEach(a => console.debug(`Alias: ${JSON.stringify(a)}`))

            return { functionResource, aliasResources, versionsToCollect }
        } catch (error) {
            console.warn(`Failed to generate metadata of ${functionName}: `, error.stack)
        }
    })

    if (listOfFunctions.length > 0 && results.length == 0) {
        console.error("Failed to generate metadata of any lambda function.")
        throw "Failed to generate metadata of any lambda function."
    }

    return {
        functionResources: results.map(x => x.functionResource),
        aliasResources: results.flatMap(x => x.aliasResources),
        versionsToCollect: results.flatMap(x => x.versionsToCollect),
    }
}

const generateFunctionVersionResources = async (versionsToCollect) =>
    await traverse(versionsToCollect, async (lambdaFunctionVersion, index) => {
        const functionNameForRequests = prop(lambdaFunctionVersion, 'version') === "$LATEST"
            ? prop(lambdaFunctionVersion, 'functionName')
            : `${prop(lambdaFunctionVersion, 'functionName')}:${prop(lambdaFunctionVersion, 'version')}`

        let eventSourceMappings = null
        try {
            eventSourceMappings = await lambdaClient.send(new ListEventSourceMappingsCommand({ FunctionName: functionNameForRequests }))
        } catch (error) {
            console.warn(`Failed to generate event source mappings of ${functionNameForRequests}: `, error.stack)
        }
        let maybePolicy = null
        try {
            maybePolicy = await lambdaClient.send(new GetPolicyCommand({ FunctionName: functionNameForRequests }))
        } catch (e) {
            // GetPolicyCommand results in an error if the lambda has no policy defined.
            // Ignore this error, and proceed with maybePolicy = null
        }
        const functionVersionResource = makeLambdaFunctionVersionResource(lambdaFunctionVersion, eventSourceMappings, maybePolicy)

        console.debug(`FunctionVersion (${index + 1}/${versionsToCollect.length}): ${JSON.stringify(functionVersionResource)}`)

        return functionVersionResource
    })

const makeLambdaFunctionResource = (f) => {
    const arn = parseLambdaFunctionArn(prop(f.Configuration, 'functionArn'))

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", prop(f.Configuration, 'functionArn')),
        stringAttr("faas.name", arn.functionName),
        stringAttr("lambda.last_update_status", prop(f.Configuration, 'lastUpdateStatus')),
    ]

    attributes.push(...convertFunctionTagsToAttributes(f.Tags))

    const reservedConcurrency = f.Concurrency?.ReservedConcurrentExecutions || f.concurrency?.reservedConcurrentExecutions
    if (reservedConcurrency) {
        attributes.push(intAttr("lambda.reserved_concurrency", reservedConcurrency))
    }

    return {
        resourceId: prop(f.Configuration, 'functionArn'),
        resourceType: "aws:lambda:function",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    }
}

const convertFunctionTagsToAttributes = tags => {
    if (!tags) {
        return []
    }
    return Object.entries(tags).map(([key, value]) => stringAttr(`cloud.tag.${key}`, value));
}

const makeLambdaFunctionVersionResource = (fv, eventSourceMappings, maybePolicy) => {
    const originalArn = prop(fv, 'functionArn')
    const arn = parseLambdaFunctionVersionArn(originalArn)
    const functionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}`
    const functionVersionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}:${prop(fv, 'version')}`
    const resourceId = functionVersionArn
    const arch = extractArchitecture(prop(fv, 'architectures'))

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", resourceId),
        stringAttr("faas.name", arn.functionName),
        stringAttr("faas.version", prop(fv, 'version')),
        intAttr("faas.max_memory", prop(fv, 'memorySize')),
        stringAttr("host.arch", arch),
        stringAttr("lambda.runtime.name", prop(fv, 'runtime')),
        intAttr("lambda.code_size", prop(fv, 'codeSize')),
        stringAttr("lambda.handler", prop(fv, 'handler')),
        stringAttr("lambda.ephemeral_storage.size", prop(prop(fv, 'ephemeralStorage'), 'size')),
        intAttr("lambda.timeout", prop(fv, 'timeout')),
        stringAttr("lambda.iam_role", prop(fv, 'role')),
        stringAttr("lambda.function_arn", functionArn),
    ]

    if (prop(fv, 'layers')) {
        prop(fv, 'layers').forEach((layer, index) => {
            attributes.push(stringAttr(`lambda.layer.${index}.arn`, prop(layer, 'arn')))
            attributes.push(stringAttr(`lambda.layer.${index}.code_size`, prop(layer, 'codeSize')))
        })
    }

    if (eventSourceMappings && eventSourceMappings.EventSourceMappings) {
        eventSourceMappings.EventSourceMappings.forEach((eventSource, index) => {
            attributes.push(stringAttr(`lambda.event_source.${index}.arn`, prop(eventSource, 'eventSourceArn')))
        })
    }

    if (maybePolicy) {
        attributes.push(stringAttr("lambda.policy", maybePolicy.Policy))
    }

    return {
        resourceId: resourceId,
        resourceType: "aws:lambda:function-version",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    }
}

const makeAliasResource = (functionName, alias) => {
    const resourceId = alias.AliasArn
    const attributes = [
        stringAttr("cloud.resource_id", resourceId),
        stringAttr("faas.name", functionName),
        stringAttr("lambda.alias.name", alias.Name),
        stringAttr("faas.version", alias.FunctionVersion),
    ]
    return {
        resourceId: resourceId,
        resourceType: "aws:lambda:function-alias",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    }
}

export const parseLambdaFunctionArn = (lambdaFunctionArn) => {
    const arn = lambdaFunctionArn.split(":");
    return {
        region: arn[3],
        accountId: arn[4],
        functionName: arn[6],
    }
}

const parseLambdaFunctionVersionArn = (lambdaFunctionVersionArn) => {
    const arn = lambdaFunctionVersionArn.split(":");
    return {
        region: arn[3],
        accountId: arn[4],
        functionName: arn[6],
        functionVersion: arn[7],
    }
}
