# Coralogix-Lambda-Manager

This Lambda Function was created pick up newly created log groups and attach them to a firehose integration that is also created by this setup.

Environment variables:

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US] | Europe | :heavy_check_mark: |
| ApiKey | The Coralogix private key which is used to validate your authenticity | | :heavy_check_mark: |
| RegexPattern | Set up this regex to match the Log Groups names that you want to automatically subscribe to Coralogix Firehose.| | :heavy_check_mark: |
| LogsFilter | Subscription filter to select which logs needs to be sent to Coralogix. Default is for Lambda Errors that are not sendable by Coralogix Lambda Layer. | | :heavy_check_mark: |
| FIREHOSE_ARN | Arn for the firehose to subscribe the log groups (By default is the firehose created by Serverless Template) | | :heavy_check_mark: |
| FIREHOSE_ROLE | Arn for the role to allow firehose subscription (By default is the role created by Serverless template) | | :heavy_check_mark: |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64] | x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |
| NotificationEmail | Failure notification email address | | |


## License

This project is licensed under the Apache-2.0 License.