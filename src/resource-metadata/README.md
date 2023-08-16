# Coralogix Resource Metadata

This application collect AWS resource metadata and sends them to your **Coralogix** account.

## Prerequisites
* Permissions to create lambda functions
* An AWS account.
* A coralogix account.
* In case you use SSM you should first deploy the [SSM lambda layer](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/create/app?applicationId=arn:aws:serverlessrepo:eu-central-1:597078901540:applications/Coralogix-Lambda-SSMLayer)

## Fields 

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US, US2].In case that you want to use Custom domain, leave this as default and write the Custom doamin in the ``CustomDomain`` filed. | Europe | :heavy_check_mark: |
| CustomDomain | The Coralogix custom domain, leave empty if you don't use Custom domain. | | |
| aplication name | The stack name of this application created via AWS CloudFormation. | | :heavy_check_mark: |
| CreateSecret | Set to False In case you want to use SSM with your secret that contains coralogix ApiKey. | True |  | 
| ApiKey | Your Coralogix secret key or incase you use your own created secret put here the name of your secret that contains the coralogix Api Key |  | :heavy_check_mark: | 
| ResourceTtlMinutes | Once a resource is collected, how long should it remain valid. | 60 | |
| Schedule | Collect metadata on a specific schedule. | rate(10 minutes) | |
| LatestVersionsPerFunction | How many latest published versions of each Lambda function should be collected. | 0 | |
| LayerARN | In case you are using SSM This is the ARN of the Coralogix Security Layer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account. | | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]. | x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 256 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |
| LatestVersionsPerFunction | How many latest published versions of each Lambda function should be collected. | 0 | | 


**Note:** Both layers and lambda need to be in the same AWS Region.

## License

This project is licensed under the Apache-2.0 License.


