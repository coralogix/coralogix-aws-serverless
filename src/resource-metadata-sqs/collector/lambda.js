import { LambdaClient, paginateListFunctions } from '@aws-sdk/client-lambda';
import { ResourceGroupsTaggingAPIClient, paginateGetResources } from '@aws-sdk/client-resource-groups-tagging-api';
import _ from 'lodash';

const validateAndExtractConfiguration = () => {
    const includeRegex = process.env.LAMBDA_FUNCTION_INCLUDE_REGEX_FILTER ? new RegExp(_.escapeRegExp(process.env.LAMBDA_FUNCTION_INCLUDE_REGEX_FILTER)) : null;
    const excludeRegex = process.env.LAMBDA_FUNCTION_EXCLUDE_REGEX_FILTER ? new RegExp(_.escapeRegExp(process.env.LAMBDA_FUNCTION_EXCLUDE_REGEX_FILTER)) : null;
    const tagFilters = process.env.LAMBDA_FUNCTION_TAG_FILTERS ? JSON.parse(process.env.LAMBDA_FUNCTION_TAG_FILTERS) : null;
    return { includeRegex, excludeRegex, tagFilters };
};
const { includeRegex, excludeRegex, tagFilters } = validateAndExtractConfiguration();

export const collectLambdaResources = async function* (region, clientConfig = {}) {
    console.info(`Collecting list of functions in ${region}`);

    let arnsMatchingTags;
    if (tagFilters) {
        arnsMatchingTags = new Set(await collectFunctionsArnsMatchingTagFilters(region, clientConfig));
    }

    const lambdaClient = new LambdaClient({ region, ...clientConfig });
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
            yield pageFunctions; // Return each page as soon as it's collected
        }
    }
};

const collectFunctionsArnsMatchingTagFilters = async (region, clientConfig) => {
    const input = {
        ResourceTypeFilters: ['lambda:function'],
        TagFilters: tagFilters,
    };
    const arns = [];
    const resourceGroupsTaggingAPIClient = new ResourceGroupsTaggingAPIClient({ region, ...clientConfig });
    for await (const page of paginateGetResources({ client: resourceGroupsTaggingAPIClient }, input)) { // this uses the maximum page size of 100
        arns.push(...page.ResourceTagMappingList.map(r => r.ResourceARN));
    }
    return arns;
};
