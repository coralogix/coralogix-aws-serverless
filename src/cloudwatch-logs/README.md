# Coralogix-CloudWatch-Logs

This application retrieves **CloudWatch** logs and sends them to your **Coralogix** account.

It requires the following parameters:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **SubsystemName** - An optional metadata field that is sent with each log and helps to classify it (default: *Log Group name*).
* **CloudWatchLogGroupName** - Has to contain one *log group* name from the set of log groups you would like to forward to **Coralogix**. If more than one groups is forwarded add each log group as a trigger to the Lambda being created by this application.
* **CloudWatchLogstreamPattern** - the logstream pattern to match against the logstream name. the default is `(?:.*)` - send all logstreams.
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.
* **NotificationEmail** - the email address to get notifications about function failures.
* **NewlinePattern** - The newline pattern that split the logs. the default is `(?:\r\n|\r|\n)`.
* **BufferCharset** - The encoding used. the default is `utf8`.
* **SamplingRate** - The sampling rate to send logs. the default is `1` - no sampling, send all.

Do not change the `FunctionMemorySize`, `FunctionTimeout`  parameters. The application should be installed in the same AWS region as the CloudWatch log group.

**Note:** You can use log field as `Application/Subsystem` names. Just use following syntax: `$.my_log.field`.

## License

This project is licensed under the Apache-2.0 License.