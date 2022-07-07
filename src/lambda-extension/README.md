# Coralogix-Lambda-Extension

This extension provides full integration of lambda function with Coralogix service.

## Usage

Add extension layer `coralogix-extension` to your function and define following environment variables:

* **CORALOGIX_PRIVATE_KEY** - A unique ID which represents your company, this Id will be sent to your mail once you register to Coralogix.
* **CORALOGIX_APP_NAME** - Used to separate your environment, e.g. *SuperApp-test/SuperApp-prod*.
* **CORALOGIX_SUB_SYSTEM** - Your application probably has multiple subsystems, for example, *Backend servers, Middleware, Frontend servers etc*.