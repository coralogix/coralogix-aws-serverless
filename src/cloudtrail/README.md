# AWS cloud trail integarion for Coralogix

Coralogix provides a seamless integration with ``AWS`` cloud so you can send your logs from anywhere and parse them according to your needs.

## Prerequisites

* An account AWS.
* An coralogix account.

## AWS Resource Manager Template Deployment

The Cloud trail integration can be deployed by clicking the link below and signing into your AWS account:

[deployment link](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-CloudTrail)


## Fields

**Application name** - The stack name of this application created via AWS CloudFormation.

**NotificationEmail** - Should the lambda will fail to execute we can send an email to notify you via SNS (requires you have a working SNS, with a validated domain).

**S3BucketName** - The name of the S3 bucket with CloudTrail logs to watch (must be in the same region asstack that you will create).

**ApplicationName** - The name of the Coralogix application you wish to assign to this lambda.

**CoralogixRegion** - The Coralogix location region, possible options are [Europe, India, Singapore, US].

**FunctionArchitecture** - Lambda function architecture, possible options are [x86_64, arm64].

**FunctionMemorySize** - The maximum allocated memory this lambda may consume, the default is 1024.

**FunctionTimeout** - The maximum time in seconds the function may be allowed to run, the default is 300.

**PrivateKey** - Your Coralogix secret key.

**SubsystemName** - The subsystem name you wish to allocate to this log shipper.

**S3KeyPrefix** - 	The prefix of the path within the log, this way you can choose if only part of your bucket is shipped.

**S3KeySuffix** - A filter for the suffix of the file path in your bucket, the default is .json.gz.
