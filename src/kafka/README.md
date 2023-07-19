# Coralogix-Kafka

This application retrieves logs from self-hosted Apache Kafka cluster and sends them to your **Coralogix** account.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.| Europe | :heavy_check_mark: |
| ApiKey | Your Coralogix secret key. |  | :heavy_check_mark: |
| ApplicationName | A mandatory metadata field that is sent with each log and helps to classify it.|  | :heavy_check_mark: |
| SubsystemName | A mandatory metadata field that is sent with each log and helps to classify it.|  | :heavy_check_mark: |
| KafkaBrokers |  Comma-delimited list of host and port pair addresses of your Kafka brokers. For example: `ip-172-31-24-139.eu-central-1.compute.internal:9092,ip-172-31-24-140.eu-central-1.compute.internal:9092,ip-172-31-24-141.eu-central-1.compute.internal:9092`.|  | :heavy_check_mark: |
| KafkaTopic | The name of the Kafka topic used to store records in your Kafka cluster.|  | :heavy_check_mark: |
| KafkaSubnets | The subnets associated with your VPC for each Kafka broker. For example: `subnet-ddc82fb7,subnet-cecbea83,subnet-45cd9f38`.|  | :heavy_check_mark: |
| KafkaSecurityGroups | The VPC security groups used to manage access to your Kafka cluster. For example: `sg-9acacef5,sg-9ac82f5`.|  | :heavy_check_mark: |
| NotificationEmail | If the lambda fails a notification email will be sent to this address via SNS (requires you have a working SNS, with a validated domain). | |  |
| BatchSize | The maximum number of records to retrieve per batch. | 100 |  |
| FunctionArchitecture | Lambda function architecture, possible options are ``x86_64``, ``arm64``.| x86_64 |  |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

The application should be installed in the same AWS region as the Kafka cluster.

**Important:** Your VPC must be able to connect to `Lambda` and `STS`. You can provide access by configuring `PrivateLink` or a `NAT Gateway`.

**Notes:**
You can dynamically set the application and subsystem names by setting the corresponding parameter above with a filter string with the following syntax:
`$.first_key.additional_key`
Example:
`$.computedValues.functionName` would use the functionName of a computedValues array as your dynamic value.

## License

This project is licensed under the Apache-2.0 License.