# DEPRECATED
## Coralogix-Lambda-Extension

This extension provides full integration of lambda function with Coralogix service.

## Usage

Add extension layer `coralogix-extension` to your function and define following environment variables:

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| CORALOGIX_PRIVATE_KEY | A unique ID which represents your company, this Id will be sent to your mail once you register to Coralogix.| | :heavy_check_mark: |
| CORALOGIX_APP_NAME | Used to separate your environment, e.g. *SuperApp-test/SuperApp-prod*.| | |
| CORALOGIX_SUB_SYSTEM | Your application probably has multiple subsystems, for example, *Backend servers, Middleware, Frontend servers etc*.| | |
| CompatibleRuntimes | Lambda Layer Version compatible runtimes | go1.x, nodejs16.x, nodejs18.x, python3.8, python3.9 | |
| AMD64SupportEnabled | Enable support of AMD64 lambdas | true | |
| ARM64SupportEnabled | Enable support of ARM64 lambdas | false | |
| RetentionPolicy | Lambda Layer Version retention policy | Retain | |