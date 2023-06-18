# Coralogix-MSK (&Kafka) Integration

This application retrieves logs from Amazon MSK Kafka cluster and sends them to your **Coralogix** account.

## Prerequisites
* AWS account (Your AWS user should have permissions to create lambdas and IAM roles).
* Coralogix account.
* MSK cluster.
* Kafka cluster.

## AWS Resource Manager Template Deployment

MSK & Kafka integration can be deployed by clicking the link below and signing into your AWS account:

[deployment link](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-MSK)

The application should be installed in the same AWS region as the MSK cluster. Make sure that after you click on deploy for the application, that you are in right region.

## Fields

**Application name** - The stack name of this application created via AWS CloudFormation.

**ApplicationName** - Application Name as it will be seen in Coralogix UI  (A mandatory metadata field that is sent with each log and helps to classify it).

**CoralogixRegion** - The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US]. In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed.

**CustomDomain** - The Coralogix custom domain,leave empty if you don't use Custom domain.

**FunctionArchitecture** - Lambda function architecture, possible options are [x86_64, arm64]. 

**FunctionMemorySize** - The maximum allocated memory this lambda may consume, the default is 1024. Don't change!

**FunctionTimeout** - The maximum time in seconds the function may be allowed to run, the default is 300. Don't change!

**MSKClusterArn** - The ARN of the Amazon MSK Kafka cluster.

**NotificationEmail** (optinal) - If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).

**PrivateKey** - Your Coralogix secret key. Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.

**SsmEnabled** - (optional) Set this to True to use AWS Secrets. This field receives only 'True' or 'False'. When enabling this field, a secret is created with the following pattern "lambda/coralogix/<AWS_REGION>/<Cloudwatch_lambda_name>". 
* **Note:** Both layers and lambda need to be in the same AWS Region.

**SubsystemName** - Sybsystem Name as it will be seen in Coralogix UI.

**Topic** - The name of the Kafka topic used to store records in your Kafka cluster.

**LayerARN** - This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account. 

---------------------
#### * **Important:** 
Your VPC must be able to connect to `Lambda` and `STS`, as well as `Secrets Manager` if you use cluster auth. You can provide access by configuring `PrivateLink` or a `NAT Gateway`.

#### * **Notes:**
You can dynamically set the application and subsystem names by setting the corresponding parameter above with a filter string with the following syntax: `$.first_key.additional_key`
Example: `$.computedValues.functionName` would use the functionName of a computedValues array as your dynamic value.

## License

This project is licensed under the Apache-2.0 License.