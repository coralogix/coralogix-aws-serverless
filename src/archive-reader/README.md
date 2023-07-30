# Coralogix-Archive-Reader

This application imports archived logs from an S3 bucket to Coralogix.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | Possible values are `Europe`, `Europe2`, `US`, `US2`,  `Singapore` or `India`. This is a **Coralogix** parameter and does not relate to your to your AWS region.| Europe | :heavy_check_mark: |
| ApiKey | Your Coralogix secret key. |  | :heavy_check_mark: |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).| | |
| FunctionArchitecture | Lambda function architecture, possible options are [x86_64, arm64]| x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 2048 | |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 600 | |

The application should be installed in the same AWS region as the S3 archive's bucket.

## License

This project is licensed under the Apache-2.0 License.
