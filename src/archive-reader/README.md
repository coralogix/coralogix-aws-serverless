# Coralogix-Archive-Reader

This application imports archived logs from an S3 bucket to Coralogix.

It requires the following parameters:
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. Choose `Europe` if your Coralogix account URL ends with `.com`, `US` if it ends with `.us` and `India` if it ends with `.in`. This is a **Coralogix** parameter and does not relate to your to your AWS region.
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. It is located in the upper left corner.

Do not change the `FunctionMemorySize` and `FunctionTimeout` parameters. The application should be installed in the same AWS region as the S3 archive's bucket.

## License

This project is licensed under the Apache-2.0 License.