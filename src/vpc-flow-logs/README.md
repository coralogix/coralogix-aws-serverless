# Warning: This Lambda Function will be deprecated on May 1st
We recommend using [Coralogix AWS Shipper](https://github.com/coralogix/coralogix-aws-shipper/tree/master)

# Coralogix-VPC-Flow-Logs

This application retrieves **VPC Flow** logs from S3 and sends them to your **Coralogix** account.

## Prerequisites
* Active VPC with flow logs
* Permissions to create lambda functions
* An AWS account.
* A coralogix account.
* in case you use Secret Manager you should first deploy the [SM lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer), you should only deploy one layer per region.


## AWS Resource Manager Template Deployment

The VPC-Flow-Logs integration can be deployed by clicking the link below and signing into your AWS account:

[deployment link](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-VPC-Flog-Logs-S3)

The application should be installed in the same AWS region as the VPC and the S3. Make sure that after you click on deploy for the application, that you are in right region.


## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| Application name | The stack name of this application created via AWS CloudFormation. |   | :heavy_check_mark: |
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US, US2].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. |  Europe | :heavy_check_mark: | 
| CustomDomain | The Coralogix custom domain,leave empty if you don't use Custom domain.| |  | 
| CreateSecret | Set to False In case you want to use secrets manager with a predefine secret that was already created and contains Coralogix Send Your Data API key. | True |  | 
| ApiKey | Your [Coralogix Send Your Data – API Key](https://coralogix.com/docs/send-your-data-api-key/) or incase you use pre created secret (created in AWS secret manager) put here the name of the secret that contains the Coralogix send your data key |  | :heavy_check_mark: | 
| ApplicationName | Application Name as it will be seen in Coralogix UI.| | :heavy_check_mark: | 
| SubsystemName | Sybsystem Name as it will be seen in Coralogix UI.| | :heavy_check_mark: | 
| S3BucketName | The name of the S3 bucket with CloudTrail logs to watch (must be in the same region as stack that you will create). |   | :heavy_check_mark: | 
| S3KeyPrefix | The prefix of the path within the log, this way you can choose if only part of your bucket is shipped.|   |  | 
| S3KeySuffix | A filter for the suffix of the file path in your bucket.|  .json.gz. |  | 
| LayerARN | In case you want to use Secret Manager This is the ARN of the Coralogix [lambda layer ](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer). | | |
| NewlinePattern | Do not change! This is the pattern for lines splitting.| (?:\r\n\|\r\|\n) | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).| | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]| x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Don't change.| 1024 | |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Don't change.| 300 | |
| BufferSize | The Coralogix logger buffer size.| 134217728 | :heavy_check_mark: |
| BlockingPattern | a regular expression for lines that should be excluded. |  |  | 
| SamplingRate | Send messages with specific rate.| 1 | :heavy_check_mark: |
| Debug | The Coralogix logger debug mode, possible options are ``true``, ``false``.| false | |

`S3KeyPrefix` and `S3KeySuffix` should be adjusted based on your configuration.

## License

This project is licensed under the Apache-2.0 License.
