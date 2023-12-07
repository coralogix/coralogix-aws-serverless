# Coralogix Resource Metadata

This application collect AWS resource metadata and sends them to your **Coralogix** account.

## Prerequisites

* Permissions to create lambda functions
* An AWS account.
* A coralogix account.
* in case you use Secret Manager you should first deploy the [SM lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer), you should only deploy one layer per region.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US, US2].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. | Europe | :heavy_check_mark: |
| CustomDomain | The Coralogix custom domain, leave empty if you don't use Custom domain. | | |
| aplication name | The stack name of this application created via AWS CloudFormation. | | :heavy_check_mark: |
| CreateSecret |  Set to False In case you want to use secrets manager with a predefine secret that was already created and contains Coralogix Send Your Data API key. | True |  |
| ApiKey | Your [Coralogix Send Your Data – API Key](https://coralogix.com/docs/send-your-data-api-key/) or incase you use pre created secret (created in AWS secret manager) put here the name of the secret that contains the Coralogix send your data key |  | :heavy_check_mark: |
| ResourceTtlMinutes | Once a resource is collected, how long should it remain valid. | 60 | |
| LatestVersionsPerFunction | How many latest published versions of each Lambda function should be collected. | 0 | |
| CollectAliases | [True/False] | False | |

| LambdaFunctionIncludeRegexFilter | If specified, only lambda functions with ARNs matching the regex will be included in the collected metadata | | |
| LambdaFunctionExcludeRegexFilter | If specified, only lambda functions with ARNs NOT matching the regex will be included in the collected metadata | | |
| LambdaFunctionTagFilters | If specified, only lambda functions with tags matching the filters will be included in the collected metadata. Values should follow the JSON syntax for --tag-filters as documented [here](https://docs.aws.amazon.com/cli/latest/reference/resourcegroupstaggingapi/get-resources.html#options) | | |
| Schedule | Collect metadata on a specific schedule. | rate(10 minutes) | |
| LayerARN | In case you want to use Secret Manager This is the ARN of the Coralogix [lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer). | | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]. | x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 256 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

**Note:** Both layers and lambda need to be in the same AWS Region.

## License

This project is licensed under the Apache-2.0 License.
