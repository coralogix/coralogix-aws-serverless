# AWS CloudWatch-logs integarion for Coralogix

Coralogix provides a predefined Lambda function to easily forward your CloudWatch logs straight to the Coralogix platform.

IF you want to use **AWS Secrets** to store the private_key, first you need to deploy Coralogix SecretLayer form AWS Serverless Repository.
Take in consideration that both layers and lambda need to be in the same AWS Region.

## Prerequisites

* AWS user with permissions to create lambdas and IAM roles.
* AWS Cloudwatch log group & log stream
* A Coralogix account.
* Optional - use ``SSM`` to add the Coralogix private key as a ``AWS secrets``. Deploy from ``AWS Serverless application repository`` the [Coralogix-Lambda-SSMLayer](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-Lambda-SSMLayer)

## AWS Resource Manager Template Deployment

The CloudWatch-logs integration deployment link and sign in to your AWS account:

[Cloudwatch-logs deployment link](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-CloudWatch)


## Fields

It requires the following parameters:

* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.

* **CloudWatchLogGroupName** - Has to contain one *log group* name from the set of log groups you would like to forward to **Coralogix**. If more than one groups is forwarded add each log group as a trigger to the Lambda being created by this application.

* **CoralogixRegion** - The Coralogix location region, possible options are [Europe, India, Singapore, US].

* **CustomDomain** - The Coralogix custom domain,leave empty if you don't use Custom domain.

* **FunctionArchitecture** - Lambda function architecture, possible options are [x86_64, arm64]. 

* **FunctionMemorySize** - The maximum allocated memory this lambda may consume, the default is 1024. Don't change

* **FunctionTimeout** - The maximum time in seconds the function may be allowed to run, the default is 300. Don't change

* **PrivateKey** - Your Coralogix secret key.

* **SubsystemName** - Sybsystem Name as it will be seen in Coralogix UI.

* **NotificationEmail** - (optinal) - If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).

* **SsmEnabled** - Set this to True to use AWS Secrets  (When enable it creates the secret in with the following pattern "lambda/coralogix/<AWS_REGION>/<Cloudwatch_lambda_name>") - optional. The field receive 'True' or 'False'. 
**Note:** Both layers and lambda need to be in the same AWS Region.


* **LayerARN** - This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account. 

Do not change the `FunctionMemorySize`, `FunctionTimeout` and `NewlinePattern` parameters. The application should be installed in the same AWS region as the CloudWatch log group.

**Note:** You can use log field as `Application/Subsystem` names. Use following syntax: `$.my_log.field`.


## License

This project is licensed under the Apache-2.0 License.
