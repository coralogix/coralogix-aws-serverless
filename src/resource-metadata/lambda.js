import assert from 'assert'
import { LambdaClient, ListFunctionsCommand, GetFunctionCommand, ListAliasesCommand, GetPolicyCommand, ListVersionsByFunctionCommand, ListEventSourceMappingsCommand } from '@aws-sdk/client-lambda'
import pLimit from 'p-limit'
import pThrottle from 'p-throttle'
import { schemaUrl, extractArchitecture, intAttr, stringAttr, traverse } from './common.js'

const validateAndExtractConfiguration = () => {
    assert(process.env.LAMBDA_API_RATE_LIMIT, "LAMBDA_API_RATE_LIMIT env var missing!")
    const rateLimit = parseInt(process.env.LAMBDA_API_RATE_LIMIT, 10)
    assert(process.env.LATEST_VERSIONS_PER_FUNCTION, "LATEST_VERSIONS_PER_FUNCTION env var missing!")
    const latestVersionsPerFunction = parseInt(process.env.LATEST_VERSIONS_PER_FUNCTION, 10)
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!")
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10)
    return { rateLimit, latestVersionsPerFunction, resourceTtlMinutes };
};
const { rateLimit, latestVersionsPerFunction, resourceTtlMinutes } = validateAndExtractConfiguration();

const lambdaClient = new LambdaClient();

export const collectLambdaResources = async () => {

    console.info("Collecting list of functions")
    const listOfFunctions = await lambdaClient.send(new ListFunctionsCommand({}))

    console.info("Collecting function details")
    const { functionResources, aliasResources, versionsToCollect } = await collectFunctionAndAliasResources(listOfFunctions)

    console.info("Collecting function version details")
    const functionVersionResources = await collectFunctionVersionResources(versionsToCollect)

    const resources = [...functionResources, ...functionVersionResources, ...aliasResources]

    resources.forEach(f =>
        console.info(`Resource: ${JSON.stringify(f)}`)
    )

    return resources
}

const collectFunctionAndAliasResources = async (listOfFunctions) => {
    // This is important, because it avoids hitting the AWS API rate limits.
    // The AWS API rate limit is 15req/s. rateLimit is typically specified to a lower value to leave some margin.
    // The rateLimit is divided by 2, because the code it does two (GetFunction count's differently) calls per function.
    const functionThrottle = pThrottle({ limit: rateLimit / 2, interval: 1000 })

    // This is just an additional protection against doing to much in parallel, but typically the throttle should kick in first.
    const limit = pLimit(10);

    const results = (await traverse(listOfFunctions.Functions, (lambdaFunctionVersionLatest) => {
        return limit(functionThrottle(async () => {
            const functionName = lambdaFunctionVersionLatest.FunctionName
            const lambdaFunction = await lambdaClient.send(new GetFunctionCommand({ FunctionName: functionName }))
            const versions = await lambdaClient.send(new ListVersionsByFunctionCommand({ FunctionName: functionName }))
            const aliases = await lambdaClient.send(new ListAliasesCommand({ FunctionName: functionName }))

            const versionsToCollect = versions.Versions.filter((version, index) => {
                return (index <= latestVersionsPerFunction) // Is either $LATEST or one of the latestVersionsPerFunction latest released versions // This relies on the fact that AWS returns the functions in latest -> oldest order
                    || (aliases.Aliases.some(alias => version.Version === alias.FunctionVersion)) // has an alias
            })

            return {
                functionResource: makeLambdaFunctionResource(lambdaFunction),
                aliasResources: aliases.Aliases.map(alias => makeAliasResource(functionName, alias)),
                versionsToCollect,
            }
        }))
    }))

    return {
        functionResources: results.map(x => x.functionResource),
        aliasResources: results.flatMap(x => x.aliasResources),
        versionsToCollect: results.flatMap(x => x.versionsToCollect),
    }
}

const collectFunctionVersionResources = async (versionsToCollect) => {
    // The rateLimit is divided by 2, because the code it does two (ListEventSourceMappingsCommand, GetPolicyCommand) calls per function version.
    const functionVersionThrottle = pThrottle({ limit: rateLimit / 2, interval: 1000 })
    // This is just an additional protection against doing to much in parallel, but typically the throttle should kick in first.
    const limit = pLimit(10);

    return await traverse(versionsToCollect, (lambdaFunctionVersion) => {
        return limit(functionVersionThrottle(async () => {
            const functionNameForRequests = lambdaFunctionVersion.Version === "$LATEST"
                ? lambdaFunctionVersion.FunctionName
                : `${lambdaFunctionVersion.FunctionName}:${lambdaFunctionVersion.Version}`

            const eventSourceMappings = await lambdaClient.send(new ListEventSourceMappingsCommand({ FunctionName: functionNameForRequests }))
            let maybePolicy = null
            try {
                maybePolicy = await lambdaClient.send(new GetPolicyCommand({ FunctionName: functionNameForRequests }))
            } catch (e) {
                // GetPolicyCommand results in an error if the lambda has no policy defined.
                // Ignore this error, and proceed with maybePolicy = null
            }
            return makeLambdaFunctionVersionResource(lambdaFunctionVersion, eventSourceMappings, maybePolicy)
        }))
    })
}

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

    if (f.Tags) {
        Object.keys(f.Tags).forEach(key => {
            attributes.push(stringAttr(`cloud.tag.${key}`, f.Tags[key]))
        })
    }

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

const makeLambdaFunctionVersionResource = (fv, eventSourceMappings, maybePolicy) => {
    const functionVersionArn = fv.FunctionArn
    const arn = parseLambdaFunctionVersionArn(fv.FunctionArn)
    const functionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}`
    const resource_id = fv.FunctionArn
    const arch = extractArchitecture(fv.Architectures)

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", resource_id),
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
        stringAttr("lambda.function_arn", fv.FunctionArn),
    ]

    if (fv.Layers) {
        fv.Layers.forEach((layer, index) => {
            attributes.push(stringAttr(`lambda.layer.${index}.arn`, layer.Arn))
            attributes.push(stringAttr(`lambda.layer.${index}.code_size`, layer.CodeSize))
        })
    }

    eventSourceMappings.EventSourceMappings.forEach((eventSource, index) => {
        attributes.push(stringAttr(`lambda.event_source.${index}.arn`, eventSource.EventSourceArn))
    })

    if (maybePolicy) {
        attributes.push(stringAttr("lambda.policy", maybePolicy.Policy))
    }

    return {
        resourceId: resource_id,
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

const parseLambdaFunctionArn = (lambdaFunctionArn) => {
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
