# Coralogix-Akamai-DataStream

Collects [Akamai DataStream](https://developer.akamai.com/api/web_performance/datastream/v1.html) logs and sends them to **Coralogix**.

In order to use this integration you first need to add a [data stream](https://learn.akamai.com/en-us/webhelp/datastream/datastream-user-guide/GUID-D35316FA-031B-480C-92C4-E2B8AD7B897E.html). You will need the data stream ID. You also need to set up an API client for the DataStream Pull API. You will need the `client API host`, `client secret`, `access token`, and `client token`.

Additional parameters that will be needed are:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **Enabled** - **Akamai’s** datastream API pulling state. Can be `true` (active) or `false` (inactive).
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.
* **Schedule** - [CloudWatch rules schedule expression](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#RateExpressions).
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.

Do not change the `FunctionMemorySize` and `FunctionTimeout` parameters.

## License

This project is licensed under the Apache-2.0 License.