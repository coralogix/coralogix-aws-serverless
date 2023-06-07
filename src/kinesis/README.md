# Coralogix-Kinesis

This application retrieves **Kinesis** stream data and sends them to your **Coralogix** account.

It requires the following parameters:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CoralogixRegion** - The Coralogix location region, possible options are [Europe, Europe2, India, Singapore, US].In case that you want to use Custom Url, leave this as default and write the `Custom Url` in the CustomUrl filed.
* **CustomUrl** - The Coralogix custom url,leave empty if you don't use Custom domain.
* **KinesisStreamArn** - The ARN for the **Kinesis** stream.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **NotificationEmail** - (optinal) - If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain).
* **SsmEnabled** - Set this to True to use AWS Secrets  (When enable it creates the secret in with the following pattern "lambda/coralogix/<AWS_REGION>/<Cloudwatch_lambda_name>") - optional. The field receive 'True' or 'False'. 
**Note:** Both layers and lambda need to be in the same AWS Region.

* **LayerARN** - This is the ARN of the Coralogix SecurityLayer. Copy from the ``SSM`` serverless application the ARN that was installed on the AWS account. 

## License

This project is licensed under the Apache-2.0 License.
