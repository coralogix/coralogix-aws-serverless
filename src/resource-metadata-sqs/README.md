# Coralogix Resource Metadata (SQS mode)

This application collect AWS resource metadata and sends them to your **Coralogix** account.

This is a specific version of the [resource-metadata](../resource-metadata) application, which is designed to:

1. Handle huge amount of Lambda functions in the target AWS Region (5000+).
2. Support cross-account and multi-region collection of metadata from multiple AWS accounts.

## Prerequisites

* Permissions to create required AWS resources (Lambda, SQS, SNS, Cloudtrail etc.)
* An AWS account.
* A coralogix account.
* in case you use Secret Manager you should first deploy the [SM lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer), you should only deploy one layer per region.
* in case you want to collect metadata from multiple AWS accounts, see [Cross-Account Collection](##cross-account-collection) for more details.

## Cross-Region Collection

To enable cross-region collection within an account, simply add the `SourceRegions` parameter. You don't need to do anything else.

## Cross-Account Collection

This function supports cross-account collection of metadata from multiple AWS accounts.

To enable this feature, you need to specify the `CrossAccountMode` parameter (`Disabled` by default). 

There are two options to collect metadata across accounts:

1. IAM Cross-account roles (`StaticIAM`): loops over account IDs (`AccountIds`), assuming IAM role in each account. IAM role should have the same name in each account (`CrossAccountIAMRoleName`).
2. AWS Config Resource Aggregator (`Config`): runs a Query on AWS Config Aggregator (`ConfigAggregatorName`). If the aggregator is in a different account, set `ConfigCrossAccountRole` to the IAM role ARN in that account; the collector will assume it when querying Config. It also requires IAM cross-account roles setup for the generator.

There are many other ways to collect the metadata about Lambda functions and EC2 instances from different accounts. See [the cross-account solutions doc](./collector/CROSSACCOUNT_SOLUTIONS.md) for more details. The rest of those options can be implemented on demand.

### Cross-account permissions

Here is the set of required IAM permissions that should be set on the target roles:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
            "ec2:DescribeInstances",
            "lambda:ListFunctions",
            "lambda:ListVersionsByFunction", 
            "lambda:GetFunctionConfiguration",
            "lambda:GetFunctionConcurrency",
            "lambda:ListTags",
            "lambda:ListAliases",
            "lambda:ListEventSourceMappings",
            "lambda:GetPolicy",
            "tag:GetResources"
      ],
      "Resource": "*"
    }
  ]
}
```

As you will know the exact functions' role ARNs only after the template is deployed, you need to follow these steps to make it work:

1. Create the roles in the target accounts, setting necessary IAM permissions, but without setting the trust relationship to the source account, since we don't know Lambda functions role ARNs yet.
2. Deploy the template with the `CrossAccountIAMRoleName` parameter, mentioning the target roles' name.
3. After the template is deployed, set the trust relationship to the source account, using the Lambda functions' role ARNs. If you're using a `StaticIAM` mode, make sure to include both `collector` and `generator` functions' role ARNs. If you're using a `Config` mode, you need to include only `generator` role ARN.

Here is an example of a trust relationship policy:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::123456789012:role/mystackname-GeneratorLambdaFunctionRole-randomid",
                    "arn:aws:iam::123456789012:role/mystackname-CollectorLambdaFunctionRole-randomid"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

After setting the trust relationship, the `generator` and `collector` functions will be able to assume the target roles and collect metadata from those accounts.

## Event Mode

Apart from running a central collector, you can enable the `EventMode` in order to get the near-real-time events from CloudTrail to the SQS queue by using EventBridge. As soon as the event appears in the queue, it gets processed by `generator` function.

### Events from the function account/region

You can enable it in two formats:

* `EnabledCreateTrail` – creates CloudTrail Trail and EventBridge Rule
* `EnabledWithExistingTrail` – creates EventBridge Rule only

### Events from other accounts/regions

You can route CloudTrail events from other accounts and regions to the function's SQS queue.

To make it work:

1. cross-account mode needs to be enabled
2. `OrganizationId` parameter has to be set
2. the function needs to have access to the source account by using IAM Assume Role
3. the Eventbridge rules have to use the following event pattern:

Lambda + EC2:

```json
{
  "detail-type": [
    "AWS API Call via CloudTrail"
  ],
  "source": [
    "aws.ec2",
    "aws.lambda"
  ],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com",
      "lambda.amazonaws.com"
    ],
    "eventName": [
      "RunInstances",
      "CreateFunction20150331"
    ],
    "errorCode": [
      {
        "exists": false
      }
    ]
  }
}
```

Lambda only:

```json
{
  "detail-type": [
    "AWS API Call via CloudTrail"
  ],
  "source": [
    "aws.lambda"
  ],
  "detail": {
    "eventSource": [
      "lambda.amazonaws.com"
    ],
    "eventName": [
      "CreateFunction20150331"
    ],
    "errorCode": [
      {
        "exists": false
      }
    ]
  }
}
```

EC2 only:

```json
{
  "detail-type": [
    "AWS API Call via CloudTrail"
  ],
  "source": [
    "aws.ec2"
  ],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com"
    ],
    "eventName": [
      "RunInstances"
    ],
    "errorCode": [
      {
        "exists": false
      }
    ]
  }
}
```

## Fields

### Coralogix Configuration Parameters

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | The Coralogix location region, possible options are [EU1, EU2, AP1, AP2, AP3, US1, US2, Custom].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. | Custom | :heavy_check_mark: |
| ApiKey | Your [Coralogix Send Your Data – API Key](https://coralogix.com/docs/send-your-data-api-key/) or incase you use pre created secret (created in AWS secret manager) put here the name of the secret that contains the Coralogix send your data key | | :heavy_check_mark: |
| CustomDomain | The Coralogix custom domain, leave empty if you don't use Custom domain. | | |

### Event Mode Parameters

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| EventMode | Additionally to the regular schedule, enable real-time processing of CloudTrail events via EventBridge for immediate generation of new resources in Coralogix [Disabled, EnabledWithExistingTrail, EnabledCreateTrail]. | Disabled | |
| OrganizationId | AWS Organization ID (starts with 'o-'). Leave empty if you want to collect metadata from the current account only. | | |

### Cross-account and cross-region parameters

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| SourceRegions | The regions to collect metadata from, separated by commas (e.g. eu-north-1,eu-west-1,us-east-1). Leave empty if you want to collect metadata from the current region only. | | |
| CrossAccountMode | The mode to collect metadata from multiple accounts[Disabled, StaticIAM, Config]. Leave Disabled if you want to collect metadata from the current account only. | Disabled | |
| ConfigAggregatorName | The name of the AWS Config Aggregator to run the query. Used if `CrossAccountMode` is set to `Config`. | | |
| ConfigCrossAccountRole | IAM role ARN in the account where the AWS Config aggregator lives. If set, the collector will assume this role when querying Config (use when the aggregator is in a different account). | | |
| AccountIds | The list of account IDs, separated by comma. Used if `CrossAccountMode` is set to `StaticIAM`. | Disabled | |
| CrossAccountIAMRoleName | The name of the IAM cross-account roles set in each source account. Used if `CrossAccountMode` is not `Disabled`. | Disabled | |

### Integration configuration

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| Schedule | Collect metadata on a specific schedule. See "Notes" for more details. | rate(30 minutes) | |
| ResourceTtlMinutes | Once a resource is collected, how long should it remain valid. See "Notes" for more details. | 60 | |
| LatestVersionsPerFunction | How many latest published versions of each Lambda function should be collected. | 0 | |
| CollectAliases | [True/False] | `False` | |
| LambdaTelemetryExporterFilter | If set to `True`, only lambda functions with `coralogix-telemetry-exporter` layer will be included in the collected metadata | `False` | |
| LambdaFunctionIncludeRegexFilter | If specified, only lambda functions with ARNs matching the regex will be included in the collected metadata | | |
| LambdaFunctionExcludeRegexFilter | If specified, only lambda functions with ARNs NOT matching the regex will be included in the collected metadata | | |
| LambdaFunctionTagFilters | If specified, only lambda functions with tags matching the filters will be included in the collected metadata. Values should follow the JSON syntax for --tag-filters as documented [here](https://docs.aws.amazon.com/cli/latest/reference/resourcegroupstaggingapi/get-resources.html#options) | | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | | |
| ExcludedEC2ResourceType | Set to true to Excluded EC2 Resource Type | `False` | |
| ExcludedLambdaResourceType | Set to true to Excluded Resource Type | `False` | |
| EC2ChunkSize | Number of resources in each EC2 batch (1-40) | 25 | |

### Lambda Configuration

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]. | x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 256 | |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 | |
| MaximumConcurrency | Maximum number of concurrent SQS messages to be processed by `generator` lambda after the collection has finished. | 5 | |

### Security configuration

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| LayerARN | In case you want to use Secret Manager This is the ARN of the Coralogix [lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer). See "Notes" for more details. | | |
| CreateSecret |  Set to False In case you want to use secrets manager with a predefine secret that was already created and contains Coralogix Send Your Data API key. | True | |



## Notes

1. Both layers and lambda need to be in the same AWS Region.
2. The `Schedule` parameter needs to be longer than the time it takes to collect the metadata. For example, if it takes 10 minutes to collect the metadata from all lambda functions, the `Schedule` parameter should be set to `rate(15 minutes)` at least.
3. The `ResourceTtlMinutes` parameter needs to be longer than the `Schedule` parameter. For example, if the `Schedule` parameter is set to `rate(15 minutes)`, the `ResourceTtlMinutes` parameter should be set to at least 20 minutes.

## License

This project is licensed under the Apache-2.0 License.
