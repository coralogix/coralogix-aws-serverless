# Coralogix-CloudWatch-Metrics

This application retrieves **CloudWatch** metrics and sends them to your **Coralogix** account.

It requires the following parameters:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CloudWatchLogGroupName** - Has to contain one log group name from the set of log groups you would like to forward to **Coralogix**. If more than one groups is forwarded add each log group as a trigger to the Lambda being created by this application.
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.
* **SubsystemName** - An optional metadata field that is sent with each log and helps to classify it (default: *Log Group name*).
* **NotificationEmail** - the email address to get notifications about function failures.
* **Metrics** - JSON array with the list of the metrics. Check the example below.

**Metrics list example**:

```json
[
  {
    "Dimensions": [
      {
        "Name": "FunctionName",
        "Value": "test-function"
      }
    ],
    "Period": 60,
    "Statistics": [
      "SampleCount",
      "Average",
      "Sum",
      "Minimum",
      "Maximum"
    ],
    "MetricName": "Invocations",
    "Namespace": "AWS/Lambda"
  },
  {
    "Dimensions": [
      {
        "Name": "FunctionName",
        "Value": "test-function"
      }
    ],
    "Period": 60,
    "Statistics": [
      "SampleCount",
      "Average",
      "Sum",
      "Minimum",
      "Maximum"
    ],
    "MetricName": "Duration",
    "Namespace": "AWS/Lambda"
  }
]
```

**Namespace:** is a container for metrics like *AWS/ApiGateway*, *AWS/Lambda* etc.
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/aws-namespaces.html

**MetricName:** each Namespace has its own available metrics, for example, AWS/Lambda has *Duration*, *Invocation*, *Error* etc.
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/lam-metricscollected.html#lambda-cloudwatch-metrics

**Dimensions:** each namespace has its own dimensions, for example, AWS/Lambda has *FunctionName*.
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/lam-metricscollected.html#lam-metric-dimensions

**Period:** is the bin size to aggregate the metrics, the default and the minimum is 60 seconds.

**Statistics:** which kind of statistics to query, the default is: `SampleCount`, `Average`, `Sum`, `Minimum`, `Maximum`.

**Note:** The list of the metrics should be minified before passing to the function.

Do not change the `FunctionMemorySize`, `FunctionTimeout` and `NewlinePattern` parameters. The application should be installed in the same AWS region as the CloudWatch log group.

## License

This project is licensed under the Apache-2.0 License.