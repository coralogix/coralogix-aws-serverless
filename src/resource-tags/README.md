# Coralogix Resource Tags

This application collect AWS resource tags and sends them to your **Coralogix** account.

## Fields 

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion |  Possible values are `Europe`, `Europe2`, `US`, `US2`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region. | Europe | :heavy_check_mark: |
| ApiKey |  Your Coralogix secret key. |  | :heavy_check_mark: |
| Schedule | Collect tags on a specific schedule | rate(10 minutes) ||
| NotificationEmail | Failure notification email address | | |
| FunctionArchitecture | LLambda function architecture [x86_64, arm64] | x86_64 | |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

The application will only collect tags for the AWS region where it is installed.

## License

This project is licensed under the Apache-2.0 License.