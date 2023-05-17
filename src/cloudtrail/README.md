# AWS cloud trail integarion for Coralogix

Coralogix provides a seamless integration with ``AWS`` cloud so you can send your logs from anywhere and parse them according to your needs.

This application retrieves cloudtrail logs from s3 and sends them to your Coralogix account.

IF you want to use AWS Secrets to store the private_key, first you need to deploy Coralogix SecretLayer form AWS Serverless Repository. Take in consideration that both layers and lambda need to be in the same AWS Region.

## Prerequisites

* An AWS account.
* An coralogix account.

## AWS Resource Manager Template Deployment

The Cloud trail integration can be deployed by clicking the link below and signing into your AWS account:

[deployment link](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-CloudTrail)


## Fields

**Application name** - The stack name of this application created via AWS CloudFormation.

**NotificationEmail** (optinal) - If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).

**S3BucketName** - The name of the S3 bucket with CloudTrail logs to watch (must be in the same region as stack that you will create).

**ApplicationName** - Application Name as it will be seen in Coralogix UI.

**CoralogixRegion** - The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed.

**CustomDomain** - The Coralogix custom domain,leave empty if you don't use Custom domain.

**FunctionArchitecture** - Lambda function architecture, possible options are [x86_64, arm64].

**FunctionMemorySize** - The maximum allocated memory this lambda may consume, the default is 1024.

**FunctionTimeout** - The maximum time in seconds the function may be allowed to run, the default is 300.

**PrivateKey** - Your Coralogix secret key.

**SubsystemName** - Sybsystem Name as it will be seen in Coralogix UI.

**S3KeyPrefix** - 	The prefix of the path within the log, this way you can choose if only part of your bucket is shipped.

**S3KeySuffix** - A filter for the suffix of the file path in your bucket, the default is .json.gz.


## License

This project is licensed under the Apache-2.0 License.
