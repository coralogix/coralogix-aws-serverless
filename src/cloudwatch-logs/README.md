# Warning: This Lambda Function will be deprecated on May 1st
We recommend using [Coralogix AWS Shipper](https://github.com/coralogix/coralogix-aws-shipper/tree/master)

# AWS CloudWatch-logs integarion for Coralogix

Coralogix provides a predefined Lambda function to easily forward your CloudWatch logs straight to the Coralogix platform.

IF you want to use **AWS Secrets** to store the private_key, first you need to deploy Coralogix SecretLayer form AWS Serverless Repository.
Take in consideration that both layers and lambda need to be in the same AWS Region.

## Prerequisites

* AWS user with permissions to create lambdas and IAM roles.
* AWS Cloudwatch log group & log stream
* A Coralogix account.
* in case you use Secret Manager you should first deploy the [SM lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer), you should only deploy one layer per region.

## AWS Resource Manager Template Deployment

The CloudWatch-logs integration deployment link and sign in to your AWS account:

[Cloudwatch-logs deployment link](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-CloudWatch)


## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| Application name | The stack name of this application created via AWS CloudFormation. |   | :heavy_check_mark: |
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US, US2].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. |  Europe | :heavy_check_mark: | 
| CustomDomain | The Coralogix custom domain,leave empty if you don't use Custom domain.| |  |
| CreateSecret | Set to False In case you want to use secrets manager with a predefine secret that was already created and contains Coralogix Send Your Data API key | True |  | 
| ApiKey | Your [Coralogix Send Your Data – API Key](https://coralogix.com/docs/send-your-data-api-key/) or incase you use pre created secret (created in AWS secret manager) put here the name of the secret that contains the Coralogix send your data key |  | :heavy_check_mark: | 
| ApplicationName | Application Name as it will be seen in Coralogix UI.|   | :heavy_check_mark: | 
| SubsystemName | Sybsystem Name as it will be seen in Coralogix UI.|   | :heavy_check_mark: | 
| CloudWatchLogGroupName | Has to contain a list of *log group* names separated by a comma(log-group1,log-group2,log-group3).|   | :heavy_check_mark: | 
| LayerARN | In case you want to use Secret Manager This is the ARN of the Coralogix [lambda layer ](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer). | | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).| | |
| NewlinePattern | Do not change! This is the pattern for lines splitting.| ``(?:\r\n\|\r\|\n)`` | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]| x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Don't change| 1024 | |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Don't change| 300 | |
| SamplingRate | Send messages with specific rate.| 1 | |
| BufferCharset | The charset to use for buffer decoding, possible options are [utf8, ascii]| utf8 | |

The application should be installed in the same AWS region as the CloudWatch log group.
 
**Note:** You can use log field as `Application/Subsystem` names. Use the following syntax: `$.my_log.field`. In case you leave subsystemName as Empty it will be populated from log group name.

## License

This project is licensed under the Apache-2.0 License.

