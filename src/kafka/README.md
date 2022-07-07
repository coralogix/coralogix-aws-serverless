# Coralogix-Kafka

This application retrieves logs from self-hosted Apache Kafka cluster and sends them to your **Coralogix** account.

It requires the following parameters:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **KafkaBrokers** - Comma-delimited list of host and port pair addresses of your Kafka brokers. For example: `ip-172-31-24-139.eu-central-1.compute.internal:9092,ip-172-31-24-140.eu-central-1.compute.internal:9092,ip-172-31-24-141.eu-central-1.compute.internal:9092`.
* **KafkaTopic** - The name of the Kafka topic used to store records in your Kafka cluster.
* **KafkaSubnets** - The subnets associated with your VPC for each Kafka broker. For example: `subnet-ddc82fb7,subnet-cecbea83,subnet-45cd9f38`.
* **KafkaSecurityGroups** - The VPC security groups used to manage access to your Kafka cluster. For example: `sg-9acacef5,sg-9ac82f5`.

Do not change the `FunctionMemorySize`, `FunctionTimeout` and `BatchSize` parameters. The application should be installed in the same AWS region as the Kafka cluster.

**Important:** Your VPC must be able to connect to `Lambda` and `STS`. You can provide access by configuring `PrivateLink` or a `NAT Gateway`.

## License

This project is licensed under the Apache-2.0 License.