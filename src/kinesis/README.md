# Coralogix-Kinesis

This application retrieves **Kinesis** stream data and sends them to your **Coralogix** account.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| Application name | The stack name of this application created via AWS CloudFormation.|  | :heavy_check_mark: |
| CoralogixRegion | The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US, US2].In case that you want to use Custom Url, leave this as default and write the `Custom Url` in the CustomUrl filed.| Europe | :heavy_check_mark: |
| CustomDomain | The Coralogix custom url,leave empty if you don't use Custom domain.| | |
| ApiKey| Your Coralogix secret key. |  | :heavy_check_mark: |
| ApplicationName | A mandatory metadata field that is sent with each log and helps to classify it.|  | :heavy_check_mark: |
| SubsystemName |  A mandatory metadata field that is sent with each log and helps to classify it.|  | :heavy_check_mark: |
| KinesisStreamArn|  The ARN for the **Kinesis** stream.|  | :heavy_check_mark: |
| NewlinePattern|  The pattern for lines splitting| (?:\r\n\|\r\|\n) |  |
| SsmEnabled|  Set this to True to use AWS Secrets  (When enable it creates the secret in with the following pattern "lambda/coralogix/<AWS_REGION>/<Cloudwatch_lambda_name>") - optional. The field receive 'True' or 'False'. | False |  |
| LayerARN | This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account. | | |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | |  |
| BufferCharset | The charset to use for buffer decoding, possible options are [utf8, ascii]| utf8 |  |
| FunctionArchitecture | Lambda function architecture, possible options are ``x86_64``, ``arm64``.| x86_64 |  |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

**Note:** Both layers and lambda need to be in the same AWS Region.


## License

This project is licensed under the Apache-2.0 License.

