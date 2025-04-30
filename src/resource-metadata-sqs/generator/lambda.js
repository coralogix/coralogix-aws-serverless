import assert from 'assert';
import { LambdaClient, GetFunctionConfigurationCommand, GetFunctionConcurrencyCommand, ListTagsCommand, ListAliasesCommand, GetPolicyCommand, ListVersionsByFunctionCommand, ListEventSourceMappingsCommand } from '@aws-sdk/client-lambda';
import { schemaUrl, extractArchitecture, intAttr, stringAttr, traverse, flatTraverse } from './common.js';
import { assumeRole, getAccountId } from './crossaccount.js';

const validateAndExtractConfiguration = () => {
    assert(process.env.LATEST_VERSIONS_PER_FUNCTION, "LATEST_VERSIONS_PER_FUNCTION env var missing!");
    const latestVersionsPerFunction = parseInt(process.env.LATEST_VERSIONS_PER_FUNCTION, 10);
    assert(process.env.RESOURCE_TTL_MINUTES, "RESOURCE_TTL_MINUTES env var missing!");
    const resourceTtlMinutes = parseInt(process.env.RESOURCE_TTL_MINUTES, 10);
    assert(process.env.COLLECT_ALIASES, "COLLECT_ALIASES env var missing!");
    const collectAliases = String(process.env.COLLECT_ALIASES).toLowerCase() === "true";
    const roleName = process.env.CROSSACCOUNT_IAM_ROLE_NAME ? process.env.CROSSACCOUNT_IAM_ROLE_NAME : "CrossAccountLambdaRole";
    return { latestVersionsPerFunction, resourceTtlMinutes, collectAliases, roleName };
};
const { latestVersionsPerFunction, resourceTtlMinutes, collectAliases, roleName } = validateAndExtractConfiguration();

export const generateLambdaResources = async (region, accountId, functions) => {
    // Normalize function objects to handle both cases
    functions = functions.map(f => ({
        functionArn: f.functionArn ?? f.FunctionArn ?? f.ResourceArn,
        functionName: f.functionName ?? f.FunctionName ?? f.ResourceId,
        ...f
    }));

    const currentAccountId = await getAccountId();
    let lambdaClient;

    if (accountId === currentAccountId) {
        // Create normal LambdaClient for the current account
        lambdaClient = new LambdaClient({ region });
    } else {
        const roleArn = `arn:aws:iam::${accountId}:role/${roleName}`;

        // Assume role and create LambdaClient with assumed credentials
        const credentials = await assumeRole(roleArn);
        lambdaClient = new LambdaClient({ region, credentials });
    }

    console.info("Generating function details");
    const { functionResources, aliasResources, versionsToCollect } = await generateFunctionAndAliasResources(lambdaClient, functions);

    console.info("Generating function version details");
    const functionVersionResources = await generateFunctionVersionResources(lambdaClient, versionsToCollect);

    const resources = [...functionResources, ...functionVersionResources, ...aliasResources];

    console.info(`Generated ${functionResources.length} functions, ${functionVersionResources.length} function versions and ${aliasResources.length} aliases`);

    return resources;
};

const generateFunctionAndAliasResources = async (lambdaClient, listOfFunctions) => {
    const results = await flatTraverse(listOfFunctions, async (lambdaFunctionVersionLatest, index) => {
        // Handle both Lambda API and EventBridge property casing
        const functionName = lambdaFunctionVersionLatest.functionName ?? lambdaFunctionVersionLatest.FunctionName;
        try {
            const lambdaFunction = await lambdaClient.send(new GetFunctionConfigurationCommand({ FunctionName: functionName }));
            const functionResource = await makeLambdaFunctionResource(lambdaFunction, lambdaClient);

            const aliases = collectAliases
                ? (await lambdaClient.send(new ListAliasesCommand({ FunctionName: functionName })))?.Aliases
                : [];
            const aliasResources = aliases.map(alias => makeAliasResource(functionName, alias));

            const versions = latestVersionsPerFunction > 0
                ? (await lambdaClient.send(new ListVersionsByFunctionCommand({ FunctionName: functionName }))).Versions
                : [lambdaFunction];

            const versionsToCollect = versions.filter((version, index) => {
                const versionNumber = version.version ?? version.Version;
                return (index <= latestVersionsPerFunction)
                    || (aliases.some(alias => versionNumber === alias.FunctionVersion));
            });

            console.debug(`Function (${index + 1}/${listOfFunctions.length}): ${JSON.stringify(functionResource)}`);
            aliasResources.forEach(a => console.debug(`Alias: ${JSON.stringify(a)}`));

            return { functionResource, aliasResources, versionsToCollect };
        } catch (error) {
            console.warn(`Failed to generate metadata of ${functionName}: `, error.stack);
        }
    });

    if (listOfFunctions.length > 0 && results.length == 0) {
        console.error("Failed to generate metadata of any lambda function.");
        throw "Failed to generate metadata of any lambda function.";
    }

    return {
        functionResources: results.map(x => x.functionResource),
        aliasResources: results.flatMap(x => x.aliasResources),
        versionsToCollect: results.flatMap(x => x.versionsToCollect),
    };
};

const generateFunctionVersionResources = async (lambdaClient, versionsToCollect) =>
    await traverse(versionsToCollect, async (lambdaFunctionVersion, index) => {
        const version = lambdaFunctionVersion.version ?? lambdaFunctionVersion.Version ?? '$LATEST';
        const functionName = lambdaFunctionVersion.functionName ?? lambdaFunctionVersion.FunctionName;
        const functionNameForRequests = version === "$LATEST"
            ? functionName
            : `${functionName}:${version}`;

        let eventSourceMappings = null;
        try {
            eventSourceMappings = await lambdaClient.send(new ListEventSourceMappingsCommand({ FunctionName: functionNameForRequests }));
        } catch (error) {
            console.warn(`Failed to generate event source mappings of ${functionNameForRequests}: `, error.stack);
        }
        let maybePolicy = null;
        try {
            maybePolicy = await lambdaClient.send(new GetPolicyCommand({ FunctionName: functionNameForRequests }));
        } catch (e) {
            // GetPolicyCommand results in an error if the lambda has no policy defined.
            // Ignore this error, and proceed with maybePolicy = null
        }
        const functionVersionResource = makeLambdaFunctionVersionResource(lambdaFunctionVersion, eventSourceMappings, maybePolicy);

        console.debug(`FunctionVersion (${index + 1}/${versionsToCollect.length}): ${JSON.stringify(functionVersionResource)}`);

        return functionVersionResource;
    });

const makeLambdaFunctionResource = async (f, lambdaClient) => {
    const functionArn = f.functionArn ?? f.FunctionArn ?? f.ResourceArn;
    const arn = parseLambdaFunctionArn(functionArn);

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", functionArn),
        stringAttr("faas.name", arn.functionName),
        stringAttr("lambda.last_update_status", f.lastUpdateStatus ?? f.LastUpdateStatus),
    ];

    const tags = await lambdaClient.send(new ListTagsCommand({ Resource: functionArn }));
    attributes.push(...convertFunctionTagsToAttributes(tags.Tags));

    const concurrency = await lambdaClient.send(new GetFunctionConcurrencyCommand({ FunctionName: functionArn }));
    const reservedConcurrency = concurrency.ReservedConcurrentExecutions;
    if (reservedConcurrency) {
        attributes.push(intAttr("lambda.reserved_concurrency", reservedConcurrency));
    }

    return {
        resourceId: functionArn,
        resourceType: "aws:lambda:function",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    };
};

const convertFunctionTagsToAttributes = tags => {
    if (!tags) {
        return [];
    }
    return Object.entries(tags).map(([key, value]) => stringAttr(`cloud.tag.${key}`, value));
};

const makeLambdaFunctionVersionResource = (fv, eventSourceMappings, maybePolicy) => {
    const originalArn = fv.functionArn ?? fv.FunctionArn;
    const arn = parseLambdaFunctionVersionArn(originalArn);
    const functionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}`;
    const version = fv.version ?? fv.Version ?? '$LATEST';
    const functionVersionArn = `arn:aws:lambda:${arn.region}:${arn.accountId}:function:${arn.functionName}:${version}`;
    const resourceId = functionVersionArn;
    const architectures = fv.architectures ?? fv.Architectures;
    const arch = extractArchitecture(architectures);

    const attributes = [
        stringAttr("cloud.provider", "aws"),
        stringAttr("cloud.platform", "aws_lambda"),
        stringAttr("cloud.account.id", arn.accountId),
        stringAttr("cloud.region", arn.region),
        stringAttr("cloud.resource_id", resourceId),
        stringAttr("faas.name", arn.functionName),
        stringAttr("faas.version", version),
        intAttr("faas.max_memory", fv.memorySize ?? fv.MemorySize),
        stringAttr("host.arch", arch),
        stringAttr("lambda.runtime.name", fv.runtime ?? fv.Runtime),
        intAttr("lambda.code_size", fv.codeSize ?? fv.CodeSize),
        stringAttr("lambda.handler", fv.handler ?? fv.Handler),
        stringAttr("lambda.ephemeral_storage.size", (fv.ephemeralStorage ?? fv.EphemeralStorage)?.size ?? (fv.ephemeralStorage ?? fv.EphemeralStorage)?.Size),
        intAttr("lambda.timeout", fv.timeout ?? fv.Timeout),
        stringAttr("lambda.iam_role", fv.role ?? fv.Role),
        stringAttr("lambda.function_arn", functionArn),
    ];

    const layers = fv.layers ?? fv.Layers;
    if (layers) {
        layers.forEach((layer, index) => {
            attributes.push(stringAttr(`lambda.layer.${index}.arn`, layer.arn ?? layer.Arn));
            attributes.push(stringAttr(`lambda.layer.${index}.code_size`, layer.codeSize ?? layer.CodeSize));
        });
    }

    if (eventSourceMappings && eventSourceMappings.EventSourceMappings) {
        eventSourceMappings.EventSourceMappings.forEach((eventSource, index) => {
            attributes.push(stringAttr(`lambda.event_source.${index}.arn`, eventSource.eventSourceArn ?? eventSource.EventSourceArn));
        });
    }

    if (maybePolicy) {
        attributes.push(stringAttr("lambda.policy", maybePolicy.Policy));
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
    };
};

const makeAliasResource = (functionName, alias) => {
    const resourceId = alias.AliasArn;
    const attributes = [
        stringAttr("cloud.resource_id", resourceId),
        stringAttr("faas.name", functionName),
        stringAttr("lambda.alias.name", alias.Name),
        stringAttr("faas.version", alias.FunctionVersion),
    ];
    return {
        resourceId: resourceId,
        resourceType: "aws:lambda:function-alias",
        attributes,
        schemaUrl,
        resourceTtl: {
            seconds: resourceTtlMinutes * 60,
            nanos: 0,
        },
    };
};

export const parseLambdaFunctionArn = (lambdaFunctionArn) => {
    const arn = lambdaFunctionArn.split(":");
    return {
        region: arn[3],
        accountId: arn[4],
        functionName: arn[6],
    };
};

const parseLambdaFunctionVersionArn = (lambdaFunctionVersionArn) => {
    const arn = lambdaFunctionVersionArn.split(":");
    return {
        region: arn[3],
        accountId: arn[4],
        functionName: arn[6],
        functionVersion: arn[7],
    };
};
