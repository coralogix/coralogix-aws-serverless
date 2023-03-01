# Coralogix-S3-via-SNS

This application retrieves logs stored on an S3 bucket and sends them to your **Coralogix** account.

It requires the following parameters:
* **SNSTopicArn** - The ARN of the `SNS` service receiving your S3 bucket notification events.
* **S3BucketName** - The name of the `S3` bucket containing the log files to process.
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.


The prefix and suffix filters of your S3 object should be adjusted within your S3 bucket's "Event Notifications" configuration.
You could also configure suffix filters within your SNS subscription rule.
`BlockingPattern` parameter optionally should contain regular expression for lines that should be excluded,

Do not change the `FunctionMemorySize`, `FunctionTimeout` and `NewlinePattern` parameters. The application should be installed in the same AWS region as the S3 bucket.

**Note:** You can use log field as `Application/Subsystem` names. Just use following syntax: `$.my_log.field`.

## License

This project is licensed under the Apache-2.0 License.
