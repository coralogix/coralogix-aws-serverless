# Coralogix Resource Metadata

This application collect AWS resource metadata and sends them to your **Coralogix** account.

## Prerequisites
* Permissions to create lambda functions
* An AWS account.
* A coralogix account.


## AWS Resource Manager Template Deployment

The Resource Metadata integration can be deployed by clicking the link below and signing into your AWS account:

[deployment link](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-Resource-Metadata)

The application will only collect metadata for the AWS region where it is installed.

# Coralogix Resource Metadata

This application collect AWS resource metadata and sends them to your **Coralogix** account.

It requires the following parameters:

**Application name** - The stack name of this application created via AWS CloudFormation.

**CoralogixRegion** - The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed.

**CustomDomain** (optinal)- The Coralogix custom domain, leave empty if you don't use Custom domain.

**FunctionArchitecture** - Lambda function architecture, possible options are [x86_64, arm64]. 

**FunctionMemorySize** - The maximum allocated memory this lambda may consume, the default is 256. Don't change.

**FunctionTimeout** - The maximum time in seconds the function may be allowed to run, the default is 300. Don't change.

**LatestVersionsPerFunction** - How many latest published versions of each Lambda function should be collected.

**NotificationEmail** (optinal) - If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).

**PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.

**ResourceTtlMinutes** - Once a resource is collected, how long should it remain valid.

**Schedule** - Collect metadata on a specific schedule.

**SsmEnabled** - Use SSM for the private key True/False'.

**LayerARN** - This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account.

**Note:** Both layers and lambda need to be in the same AWS Region.

## License

This project is licensed under the Apache-2.0 License.

