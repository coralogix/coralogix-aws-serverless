# Coralogix-MSK (&Kafka) Integration

This application retrieves logs from Amazon MSK Kafka cluster and sends them to your **Coralogix** account.

## Prerequisites
* AWS account (Your AWS user should have permissions to create lambdas and IAM roles).
* Coralogix account.
* MSK cluster.
* Kafka cluster.
* in case you use Secret Manager you should first deploy the [SM lambda layer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer), you should only deploy one layer per region.

## AWS Resource Manager Template Deployment

MSK & Kafka integration can be deployed by clicking the link below and signing into your AWS account:

[deployment link](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-MSK)

The application should be installed in the same AWS region as the MSK cluster. Make sure that after you click on deploy for the application, that you are in right region.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| Application name | The stack name of this application created via AWS CloudFormation.|  | :heavy_check_mark: |
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US, US2]. In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed.| Europe | :heavy_check_mark: |
| CustomDomain | The Coralogix custom domain,leave empty if you don't use Custom domain. | | |
| ApiKey | Your Coralogix Data API Key. | | :heavy_check_mark: |
| ApplicationName | Application Name as it will be seen in Coralogix UI  (A mandatory metadata field that is sent with each log and helps to classify it). | | :heavy_check_mark: |
| SubsystemName | Sybsystem Name as it will be seen in Coralogix UI. | | :heavy_check_mark: |
| MSKClusterArn | The ARN of the Amazon MSK Kafka cluster | | :heavy_check_mark: |
| Topic | The name of the Kafka topic used to store records in your Kafka cluster. | | :heavy_check_mark: |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | | |
| LayerARN |  In case you want to use Secret Manager This is the ARN of the Coralogix [lambda layer ](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer). |  |  |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]| x86_64 |  |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

---------------------
#### * **Important:** 
Your VPC must be able to connect to `Lambda` and `STS`, as well as `Secrets Manager` if you use cluster auth. You can provide access by configuring `PrivateLink` or a `NAT Gateway`.

#### * **Notes:**
You can dynamically set the application and subsystem names by setting the corresponding parameter above with a filter string with the following syntax: `$.first_key.additional_key`
Example: `$.computedValues.functionName` would use the functionName of a computedValues array as your dynamic value.

**Notes:**
You can dynamically set the application and subsystem names by setting the corresponding parameter above with a filter string with the following syntax:
`$.first_key.additional_key`
Example:
`$.computedValues.functionName` would use the functionName of a computedValues array as your dynamic value.

## License

This project is licensed under the Apache-2.0 License.
