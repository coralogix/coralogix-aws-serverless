# AWS S3 integarion for Coralogix

This application retrieves logs stored on an S3 bucket and sends them to your **Coralogix** account. 
Coralogix provides a seamless integration with ``AWS`` cloud so you can send your logs from anywhere and parse them according to your needs.

## Prerequisites

* AWS account.
* Coralogix account.
* OPTIONAL- AWS S3 bucket.

## AWS Resource Manager Template Deployment

The S3 integration can be deployed by clicking the link below and signing into your AWS account:
[Deployment link](https://eu-central-1.console.aws.amazon.com/lambda/home?region=eu-central-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-S3)


## Fields

* **Application name** - The stack name of this application created via AWS CloudFormation.

* **NotificationEmail** - If the lambda's execute fails an auto email sends to this address to notify it via SNS (requires you have a working SNS, with a validated domain).

* **S3BucketName** - The name of your S3 bucket.

* **ApplicationName** - The name of the Coralogix application you wish to assign to this lambda.

* **BlockingPattern** - OPTIONAL, The pattern for lines blocking.

* **BufferSize** - The Coralogix logger buffer size, possible option is ``134217728``.

* **CoralogixRegion** - The Coralogix location region, possible options are ``Europe``, ``India``, ``Singapore``, ``US``.

* **CustomDomain** - Your Custom URL for the Coralogix account. Ignore unless you have a custom URL. 

* **Debug** - The Coralogix logger debug mode, possible options are ``true``, ``false``.

* **FunctionArchitecture** - Lambda function architecture, possible options are ``x86_64``, ``arm64``.

* **FunctionMemorySize** - Do not change! This is the maximum allocated memory that this lambda can consume, the default is ``1024``.

* **FunctionTimeout** - Do not change! This is the maximum time in seconds the function may be allowed to run, the default is ``300``.

* **NewlinePattern** - Do not change! This is the pattern for lines splitting, the default is ``(?:\r\n|\r|\n)``.

* **PrivateKey** - Your Coralogix secret key. Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.

* **SamplingRate** - Send messages with specific rate, the default is ``1``.

* **SubsystemName** - The subsystem name you wish to allocate to this log shipper.

* **S3KeyPrefix** - 	OPTIONAL, The prefix of the path within the log, this way you can choose if only part of your bucket is shipped.

* **S3KeySuffix** - OPTIONAL, A filter for the suffix of the file path in your bucket.


## License

This project is licensed under the Apache-2.0 License.