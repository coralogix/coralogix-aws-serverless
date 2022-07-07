# Coralogix-MSK

This application retrieves logs from Amazon MSK Kafka cluster and sends them to your **Coralogix** account.

It requires the following parameters:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **MSKClusterArn** - The ARN of the Amazon MSK Kafka cluster.
* **Topic** - The name of the Kafka topic used to store records in your Kafka cluster.

Do not change the `FunctionMemorySize` and `FunctionTimeout` parameters. The application should be installed in the same AWS region as the MSK Kafka cluster.

**Important:** Your VPC must be able to connect to `Lambda` and `STS`, as well as `Secrets Manager` if you use cluster auth. You can provide access by configuring `PrivateLink` or a `NAT Gateway`.

## License

This project is licensed under the Apache-2.0 License.