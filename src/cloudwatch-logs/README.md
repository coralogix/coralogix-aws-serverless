# AWS CloudWatch-logs integarion for Coralogix

Coralogix provides a predefined Lambda function to easily forward your CloudTrail logs straight to the Coralogix platform.

This application retrieves **CloudWatch** logs and sends them to your **Coralogix** account.

IF you want to use **AWS Secrets** to store the private_key, first you need to deploy Coralogix SecretLayer form AWS Serverless Repository.
Take in consideration that both layers and lambda need to be in the same AWS Region.

## Prerequisites

* AWS user with permissions to create lambdas and IAM roles.
* AWS Cloudwatch log group & log stream
* A Coralogix account.
* Optional - use ``SSM`` to add the Coralogix private key as a ``AWS secrets``. Deploy from ``AWS Serverless application repository`` the [Coralogix-Lambda-SSMLayer](https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-Lambda-SSMLayer)

## AWS Resource Manager Template Deployment

The CloudWatch-logs integration deployment link and sign in to your AWS account:

[Cloudwatch-logs deployment link]([https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-CloudWatch](https://serverlessrepo.aws.amazon.com/applications/eu-central-1/597078901540/Coralogix-CloudWatch))


## Fields

It requires the following parameters:

* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.

* **CloudWatchLogGroupName** - Has to contain one *log group* name from the set of log groups you would like to forward to **Coralogix**. If more than one groups is forwarded add each log group as a trigger to the Lambda being created by this application.

* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.

* **CustomDomain** - An optional field for custom domain that receive an URL. 

* **PrivateKey** - Can be found in your **Coralogix** account under `Data Flow` -> `API Keys`, it is located on the bar on top of the page. The Coralogix private key is under `Send Your Data`. 

* **SubsystemName** - An optional metadata field that is sent with each log and helps to classify it (default: *Log Group name*).

* **NotificationEmail** - The email address to get notifications about function failures.

* **SsmEnabled** - Set this to True to use AWS Secrets  (When enable it creates the secret in with the following pattern "lambda/coralogix/<AWS_REGION>/<Cloudwatch_lambda_name>") - optional. The field receive 'True' or 'False'. 
**Note:** Both layers and lambda need to be in the same AWS Region.


* **LayerARN** - This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account. 

Do not change the `FunctionMemorySize`, `FunctionTimeout` and `NewlinePattern` parameters. The application should be installed in the same AWS region as the CloudWatch log group.

**Note:** You can use log field as `Application/Subsystem` names. Use following syntax: `$.my_log.field`.


## License

This project is licensed under the Apache-2.0 License.
