# Coralogix-SNS

This application retrieves **SNS** message and sends them to your **Coralogix** account.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | Possible values are `Europe`, `Europe2`, `US`, `US2`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region. | Europe | :heavy_check_mark: |
| ApiKey | Your Coralogix secret key. |   | :heavy_check_mark: |
| ApplicationName | A mandatory metadata field that is sent with each log and helps to classify it.|   | :heavy_check_mark: |
| SubsystemName | An mandatory metadata field that is sent with each log and helps to classify it.|   | :heavy_check_mark: |
| SNSTopicArn | The ARN of SNS topic to subscribe.|   | :heavy_check_mark: |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).| | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]| x86_64 ||
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

The application should be installed in the same AWS region as the CloudWatch log group.

**Note:** You can use log field as `Application/Subsystem` names. Just use following syntax: `$.my_log.field`.

## License

This project is licensed under the Apache-2.0 License.

