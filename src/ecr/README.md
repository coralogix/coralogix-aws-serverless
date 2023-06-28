# ECR Image Vulnerability Scan to Coralogix

This application fetches image scan findings from Elastic Container Registry and sends them to your Coralogix account.

It requires the following parameters:
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **CoralogixDomain** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`.
  * `Europe` - teamname.coralogix.com
  * `Europe2` - teamname.eu2.app.coralogix.com
  * `US` - teamname.app.coralogix.us
  * `India` - teamname.app.coralogix.in
  * `Singapore` - teamname.app.coralogixsg.com
  >This is a **Coralogix** parameter and does not relate to the AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.

> * Use caution when changing the FunctionMemorySize and FunctionTimeout parameters.
> * The application should be installed in the same AWS region as the ECR repository.

## License

This project is licensed under the Apache-2.0 License.