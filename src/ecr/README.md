# ECR Image Vulnerability Scan to Coralogix

This application fetches image scan findings from Elastic Container Registry and sends them to your Coralogix account.

## Fields

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CoralogixRegion | Possible values are `Europe`, `Europe2`, `US`, `US2`, `Singapore` or `India`. This is a **Coralogix** parameter and does not relate to your to your AWS region.| Europe | :heavy_check_mark: |
| CustomDomain | The Coralogix custom domain,leave empty if you don't use Custom domain. | |  | 
| ApiKey | Your Coralogix secret key.|  | :heavy_check_mark: |
| ApplicationName | A mandatory metadata field that is sent with each log and helps to classify it.|  | :heavy_check_mark: |
| SubsystemName | A mandatory metadata field that is sent with each log and helps to classify it.|  | :heavy_check_mark: |
| FunctionArchitecture | Lambda function architecture, possible options are ``x86_64``, ``arm64``.| x86_64 |  |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. Default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. Default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |

> * The application should be installed in the same AWS region as the ECR repository.

## License

This project is licensed under the Apache-2.0 License.