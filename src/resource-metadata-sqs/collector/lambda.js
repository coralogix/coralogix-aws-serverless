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

export const collectLambdaResources = async () => {

    console.info("Collecting list of functions")
    const listOfFunctions = [];
    for await (const page of paginateListFunctions({ client: lambdaClient }, {})) { // this uses the maximum page size of 50
        listOfFunctions.push(...page.Functions);
    }
    if (includeRegex) {
        listOfFunctions = listOfFunctions.filter(f => includeRegex.test(f.FunctionArn))
    }
    if (excludeRegex) {
        listOfFunctions = listOfFunctions.filter(f => !excludeRegex.test(f.FunctionArn))
    }
    if (tagFilters) {
        const arns = new Set(await collectFunctionsArnsMatchingTagFilters());
        listOfFunctions = listOfFunctions.filter(f => arns.has(f.FunctionArn))
    }

    return listOfFunctions
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
