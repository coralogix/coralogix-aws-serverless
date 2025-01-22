import assert from 'assert'
import { LambdaClient, GetFunctionCommand, ListAliasesCommand, GetPolicyCommand, ListVersionsByFunctionCommand, ListEventSourceMappingsCommand } from '@aws-sdk/client-lambda'
import { ResourceGroupsTaggingAPIClient, paginateGetResources } from '@aws-sdk/client-resource-groups-tagging-api';
import { schemaUrl, extractArchitecture, intAttr, stringAttr, traverse, flatTraverse } from './common.js'

const validateAndExtractConfiguration = () => {
    assert(process.env.LATEST_VERSIONS_PER_FUNCTION, "LATEST_VERSIONS_PER_FUNCTION env var missing!")
    const latestVersionsPerFunction = parseInt(process.env.LATEST_VERSIONS_PER_FUNCTION, 10)
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!")
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10)
    assert(process.env.COLLECT_ALIASES, "COLLECT_ALIASES env var missing!")
    const collectAliases = String(process.env.COLLECT_ALIASES).toLowerCase() === "true"
    const includeRegex = process.env.LAMBDA_FUNCTION_INCLUDE_REGEX_FILTER ? new RegExp(process.env.LAMBDA_FUNCTION_INCLUDE_REGEX_FILTER) : null
    const excludeRegex = process.env.LAMBDA_FUNCTION_EXCLUDE_REGEX_FILTER ? new RegExp(process.env.LAMBDA_FUNCTION_EXCLUDE_REGEX_FILTER) : null
    const tagFilters = process.env.LAMBDA_FUNCTION_TAG_FILTERS ? JSON.parse(process.env.LAMBDA_FUNCTION_TAG_FILTERS) : null
    return { latestVersionsPerFunction, resourceTtlMinutes, collectAliases, includeRegex, excludeRegex, tagFilters };
}
const { latestVersionsPerFunction, resourceTtlMinutes, collectAliases, includeRegex, excludeRegex, tagFilters } = validateAndExtractConfiguration();

const lambdaClient = new LambdaClient();
const resourceGroupsTaggingAPIClient = tagFilters ? new ResourceGroupsTaggingAPIClient() : null;

export const generateLambdaResources = async (functions) => {

    if (includeRegex) {
        functions = functions.filter(f => includeRegex.test(f.FunctionArn))
    }
    if (excludeRegex) {
        functions = functions.filter(f => !excludeRegex.test(f.FunctionArn))
    }
    if (tagFilters) {
        const arns = new Set(await generateFunctionsArnsMatchingTagFilters());
        functions = functions.filter(f => arns.has(f.FunctionArn))
    }

    console.info("Generating function details")
    const { functionResources, aliasResources, versionsToCollect } = await generateFunctionAndAliasResources(functions)

    console.info("Generating function version details")
    const functionVersionResources = await generateFunctionVersionResources(versionsToCollect)

    const resources = [...functionResources, ...functionVersionResources, ...aliasResources]

    console.info(`Generated ${functionResources.length} functions, ${functionVersionResources.length} function versions and ${aliasResources.length} aliases`)

    return resources
}


const generateFunctionsArnsMatchingTagFilters = async () => {
    const input = {
        ResourceTypeFilters: ['lambda:function'],
        TagFilters: tagFilters,
    };
    const arns = [];
    for await (const page of paginateGetResources({ client: resourceGroupsTaggingAPIClient }, input)) { // this uses the maximum page size of 100
        arns.push(...page.ResourceTagMappingList.map(r => r.ResourceARN));
    }
    return arns
}

const generateFunctionAndAliasResources = async (listOfFunctions) => {
    const results = await flatTraverse(listOfFunctions, async (lambdaFunctionVersionLatest, index) => {
        const functionName = lambdaFunctionVersionLatest.FunctionName
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
                return (index <= latestVersionsPerFunction) // Is either $LATEST or one of the latestVersionsPerFunction latest released versions // This relies on the fact that AWS returns the functions in latest -> oldest order
                    || (aliases.some(alias => version.Version === alias.FunctionVersion)) // has an alias
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
        const functionNameForRequests = lambdaFunctionVersion.Version === "$LATEST"
            ? lambdaFunctionVersion.FunctionName
            : `${lambdaFunctionVersion.FunctionName}:${lambdaFunctionVersion.Version}`

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
    const arn = parseLambdaFunctionArn(f.Configuration.FunctionArn)

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", f.Configuration.FunctionArn),
        stringAttr("faas.name", arn.functionName),
        stringAttr("lambda.last_update_status", f.Configuration.LastUpdateStatus),
    ]

    attributes.push(...convertFunctionTagsToAttributes(f.Tags))

    const reservedConcurrency = f.Concurrency?.ReservedConcurrentExecutions
    if (reservedConcurrency) {
        attributes.push(intAttr("lambda.reserved_concurrency", reservedConcurrency))
    }

    return {
        resourceId: f.Configuration.FunctionArn,
        resourceType: "aws:lambda:function",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    }
}

// WARNING the tags data structure is different in lambda and in ec2
const convertFunctionTagsToAttributes = tags => {
    if (!tags) {
        return []
    }
    return Object.entries(tags).map(([key, value]) => stringAttr(`cloud.tag.${key}`, value));
}

const makeLambdaFunctionVersionResource = (fv, eventSourceMappings, maybePolicy) => {
    const originalArn = fv.FunctionArn // this may be a function version arn or a function arn
    const arn = parseLambdaFunctionVersionArn(originalArn)
    const functionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}`
    const functionVersionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}:${fv.Version}`
    const resourceId = functionVersionArn
    const arch = extractArchitecture(fv.Architectures)

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", resourceId),
        stringAttr("faas.name", arn.functionName),
        stringAttr("faas.version", fv.Version),
        intAttr("faas.max_memory", fv.MemorySize),
        stringAttr("host.arch", arch),
        stringAttr("lambda.runtime.name", fv.Runtime),
        intAttr("lambda.code_size", fv.CodeSize),
        stringAttr("lambda.handler", fv.Handler),
        stringAttr("lambda.ephemeral_storage.size", fv.EphemeralStorage.Size),
        intAttr("lambda.timeout", fv.Timeout),
        stringAttr("lambda.iam_role", fv.Role),
        stringAttr("lambda.function_arn", functionArn),
    ]

    if (fv.Layers) {
        fv.Layers.forEach((layer, index) => {
            attributes.push(stringAttr(`lambda.layer.${index}.arn`, layer.Arn))
            attributes.push(stringAttr(`lambda.layer.${index}.code_size`, layer.CodeSize))
        })
    }

    if (eventSourceMappings && eventSourceMappings.EventSourceMappings) {
        eventSourceMappings.EventSourceMappings.forEach((eventSource, index) => {
            attributes.push(stringAttr(`lambda.event_source.${index}.arn`, eventSource.EventSourceArn))
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
