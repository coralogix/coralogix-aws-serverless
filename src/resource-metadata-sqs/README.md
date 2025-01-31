# Coralogix Resource Metadata (SQS mode)

This application collect AWS resource metadata and sends them to your **Coralogix** account.

This is a specific version of the [resource-metadata](../resource-metadata) application, which is designed to handle huge amount of Lambda functions in the target AWS Region (5000+).

## Prerequisites

* Permissions to create required AWS resources (Lambda, SQS, SNS, Cloudtrail etc.)
* An AWS account.
* A coralogix account.
* in case you use Secret Manager you should first deploy the [SM lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer), you should only deploy one layer per region.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | The Coralogix location region, possible options are [EU1, EU2, AP1, AP2, AP3, US1, US2, Custom].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. | Custom | :heavy_check_mark: |
| CustomDomain | The Coralogix custom domain, leave empty if you don't use Custom domain. | | |
| aplication name | The stack name of this application created via AWS CloudFormation. | | :heavy_check_mark: |
| CreateSecret |  Set to False In case you want to use secrets manager with a predefine secret that was already created and contains Coralogix Send Your Data API key. | True | |
| ApiKey | Your [Coralogix Send Your Data – API Key](https://coralogix.com/docs/send-your-data-api-key/) or incase you use pre created secret (created in AWS secret manager) put here the name of the secret that contains the Coralogix send your data key | | :heavy_check_mark: |
| EventMode | Additionally to the regular schedule, enable real-time processing of CloudTrail events via EventBridge for immediate generation of new resources in Coralogix [Disabled, EnabledWithExistingTrail, EnabledCreateTrail]. | Disabled | |
| ResourceTtlMinutes | Once a resource is collected, how long should it remain valid. See "Notes" for more details. | 60 | |
| LatestVersionsPerFunction | How many latest published versions of each Lambda function should be collected. | 0 | |
| CollectAliases | [True/False] | False | |
| LambdaFunctionIncludeRegexFilter | If specified, only lambda functions with ARNs matching the regex will be included in the collected metadata | | |
| LambdaFunctionExcludeRegexFilter | If specified, only lambda functions with ARNs NOT matching the regex will be included in the collected metadata | | |
| LambdaFunctionTagFilters | If specified, only lambda functions with tags matching the filters will be included in the collected metadata. Values should follow the JSON syntax for --tag-filters as documented [here](https://docs.aws.amazon.com/cli/latest/reference/resourcegroupstaggingapi/get-resources.html#options) | | |
| ExcludedEC2ResourceType | Set to true to Excluded EC2 Resource Type | `False` | |
| ExcludedLambdaResourceType | Set to true to Excluded Resource Type | `False` | |
| Schedule | Collect metadata on a specific schedule. See "Notes" for more details. | rate(30 minutes) | |
| LayerARN | In case you want to use Secret Manager This is the ARN of the Coralogix [lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer). See "Notes" for more details. | | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]. | x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 256 | |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 | |
| MaximumConcurrency | Maximum number of concurrent SQS messages to be processed by `generator` lambda after the collection has finished. | 5 | |

## Notes

1. Both layers and lambda need to be in the same AWS Region.
2. The `Schedule` parameter needs to be longer than the time it takes to collect the metadata. For example, if it takes 10 minutes to collect the metadata from all lambda functions, the `Schedule` parameter should be set to `rate(15 minutes)` at least.
3. The `ResourceTtlMinutes` parameter needs to be longer than the `Schedule` parameter. For example, if the `Schedule` parameter is set to `rate(15 minutes)`, the `ResourceTtlMinutes` parameter should be set to at least 20 minutes.

## License

This project is licensed under the Apache-2.0 License.
