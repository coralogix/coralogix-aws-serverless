# Coralogix EventLogFile 

This application retrieves event log files from Salesforce api and sends them to your **Coralogix** account.

It requires the following parameters:

## Coralogix Configuration
* **CoralogixRegion** - Possible values are `Europe`, `Europe2`, `US`, `Singapore` or `India`. to learn more about your region and domain go [here](https://coralogix.com/docs/coralogix-domain/).
* **PrivateKey** - Can be found in your **Coralogix** account under `Settings` -> `Send your logs`. to learn more about your private key go [here](https://coralogix.com/docs/private-key/).
* **ApplicationName** - A mandatory metadata field that is sent with each log and helps to classify it.
* **SubsystemName** - A mandatory metadata field that is sent with each log and helps to classify it.  
  
To learn more about application name and subsystem name go [here](https://coralogix.com/docs/application-and-subsystem-names/)

## Event-log Configuration

* **SFSandbox** -  True or False if this is a sandbox environment.
* **SFHost** - A mandatory field, the Salesforce host without '.my.salesforce.com'; <SF-HOST>.my.salesforce.com.
* **SFEventType** - The wanted event to get logs for, leave empty for all events.
* **SFClientId** -  A mandatory field, the salesforce application client id. used to get authenticated.
* **SFClientSecret** - A mandatory field, the salesforce application client secret. used to get authenticated.
* **SFUsername** - A mandatory field, the salesforce username. used to get authenticated.
* **SFPassword** - A mandatory field, the salesforce password. used to get authenticated.
    
## Lambda Configuration

* **FunctionArchitecture** - Lambda function architecture [x86_64, arm64].
* **FunctionMemorySize** - Lambda function memory limit.
* **FunctionTimeout** - Lambda function timeout limit.
* **FunctionSchedule** - Lambda function schedule in hours, the function will be invoked each X hours. after deploy first invocation will be after X hours.
* **NotificationEmail** - Failure notification email address.

## Script Configuration

* **LogsToStdout** - Send logs to stdout/cloudwatch. Possible values are `True`, `False`.

## License

This project is licensed under the Apache-2.0 License.