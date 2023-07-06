# AWS S3 integarion for Coralogix

Coralogix provides a predefined Lambda function to easily forward your S3 logs straight to the Coralogix platform.

## Prerequisites

* AWS account (Your AWS user should have permissions to create lambdas and IAM roles).
* Coralogix account.
* AWS S3 bucket.

## AWS Resource Manager Template Deployment

The S3 integration can be deployed by clicking the link below and signing into your AWS account:
[Deployment link](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-S3)


## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| Application name | The stack name of this application created via AWS CloudFormation. |   | :heavy_check_mark: |
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. |  Europe | :heavy_check_mark: | 
| CustomDomain | The Coralogix custom domain,leave empty if you don't use Custom domain. |   |  | 
| ApiKey | Your Coralogix secret key. |   | :heavy_check_mark: | 
| ApplicationName | Application Name as it will be seen in Coralogix UI. |   | :heavy_check_mark: | 
| SubsystemName | Sybsystem Name as it will be seen in Coralogix UI. |   | :heavy_check_mark: | 
| S3BucketName | The name of the S3 bucket with CloudTrail logs to watch (must be in the same region as stack that you will create). |   | :heavy_check_mark: | 
| S3KeyPrefix | The prefix of the path within the log, this way you can choose if only part of your bucket is shipped. |   |  | 
| S3KeySuffix | A filter for the suffix of the file path in your bucket, the default is  |  .json.gz. |  | 
| SsmEnabled | Set this to True to use AWS Secrets  (When enable it creates the secret in with the following pattern "lambda/coralogix/<AWS_REGION>/<Cloudwatch_lambda_name>"). The field receive 'True' or 'False'. **Note:** Both layers and lambda need to be in the same AWS Region.|  False | :heavy_check_mark: |
| LayerARN | This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account.| | |
| NewlinePattern | Do not change! This is the pattern for lines splitting.| (?:\r\n|\r|\n) | :heavy_check_mark: |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).| | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]| x86_64 | :heavy_check_mark: |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Don't change| 1024 | :heavy_check_mark: |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Don't change| 300 | :heavy_check_mark: |
| BufferSize | The Coralogix logger buffer size.| 134217728 | :heavy_check_mark: |
| BlockingPattern | a regular expression for lines that should be excluded.  |  |  | 
| SamplingRate | Send messages with specific rate.| 1 | :heavy_check_mark: |
| Debug | The Coralogix logger debug mode, possible options are ``true``, ``false``.| false | :heavy_check_mark: |


**Note:** You can use log field as Application/Subsystem names. Just use following syntax: ``$.my_log.field``.

## License

This project is licensed under the Apache-2.0 License.
