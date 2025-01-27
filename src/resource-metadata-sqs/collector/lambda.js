import { LambdaClient, paginateListFunctions } from '@aws-sdk/client-lambda'
import { ResourceGroupsTaggingAPIClient, paginateGetResources } from '@aws-sdk/client-resource-groups-tagging-api';

const validateAndExtractConfiguration = () => {
    const includeRegex = process.env.LAMBDA_FUNCTION_INCLUDE_REGEX_FILTER ? new RegExp(process.env.LAMBDA_FUNCTION_INCLUDE_REGEX_FILTER) : null
    const excludeRegex = process.env.LAMBDA_FUNCTION_EXCLUDE_REGEX_FILTER ? new RegExp(process.env.LAMBDA_FUNCTION_EXCLUDE_REGEX_FILTER) : null
    const tagFilters = process.env.LAMBDA_FUNCTION_TAG_FILTERS ? JSON.parse(process.env.LAMBDA_FUNCTION_TAG_FILTERS) : null
    return { includeRegex, excludeRegex, tagFilters };
}
const { includeRegex, excludeRegex, tagFilters } = validateAndExtractConfiguration();

const lambdaClient = new LambdaClient();
const resourceGroupsTaggingAPIClient = tagFilters ? new ResourceGroupsTaggingAPIClient() : null;

export const collectLambdaResources = async function* () {
    console.info("Collecting list of functions")

    let arnsMatchingTags;
    if (tagFilters) {
        arnsMatchingTags = new Set(await collectFunctionsArnsMatchingTagFilters());
    }

    while (true) {
        try {
            for await (const page of paginateListFunctions({ client: lambdaClient }, { MaxItems: 50 })) {
                let pageFunctions = page.Functions;

                if (includeRegex) {
                    pageFunctions = pageFunctions.filter(f => includeRegex.test(f.FunctionArn));
                }

                if (excludeRegex) {
                    pageFunctions = pageFunctions.filter(f => !excludeRegex.test(f.FunctionArn));
                }

                if (tagFilters) {
                    pageFunctions = pageFunctions.filter(f => arnsMatchingTags.has(f.FunctionArn));
                }

                if (pageFunctions.length > 0) {
                    yield pageFunctions;
                }
            }
            break; // If we get here, pagination completed successfully
        } catch (error) {
            if (error.name === 'TooManyRequestsException') {
                console.warn('Rate limit exceeded, waiting 30 seconds before retrying...');
                await new Promise(resolve => setTimeout(resolve, 30000));
                continue;
            }
            throw error; // Re-throw any other errors
        }
    }
}

const collectFunctionsArnsMatchingTagFilters = async () => {
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
