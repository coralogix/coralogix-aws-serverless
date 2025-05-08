# Coralogix-Lambda-Manager

This Lambda Function was created pick up newly created and existing log groups and attach them to Firehose or Lambda integration

Environment variables:

| Parameter | Description | Default Value | Required |
|---|---|---|---|
| RegexPattern | Set up this regex to match the Log Groups names that you want to automatically subscribe to the destination| | :heavy_check_mark: |
| LogsFilter | Subscription filter to select which logs needs to be sent to Coralogix. For Example for Lambda Errors that are not sendable by Coralogix Lambda Layer '?REPORT ?"Task timed out" ?"Process exited before completing" ?errorMessage ?"module initialization error:" ?"Unable to import module" ?"ERROR Invoke Error" ?"EPSAGON_TRACE:"'. | | :heavy_check_mark: |
| DESTINATION_ARN | Arn for the firehose / lambda to subscribe the log groups | | :heavy_check_mark: |
| DESTINATION_ROLE | Arn for the role to allow destination subscription to be pushed (needed only for Firehose) | | :heavy_check_mark: |
| DISABLE_ADD_PERMISSION | Skip Adding LogGroup Permission for lambda | false | |
| DESTINATION_TYPE | Type of destination (Lambda or Firehose) | | :heavy_check_mark: |
| SCAN_OLD_LOGGROUPS | When set to true, the lambda will scan all existing log group and add the ones that match the RegexPattern as a trigger, the scan will only happen on the creation of the lambda after that it will only detect a new log group. | false | |
| ADD_PERMISSIONS_TO_ALL_LOG_GROUPS | When set to true, the code will allow all existing and new log groups using a wildcard to subscribe to the destination. | false | |
| LogGroupPermissionPreFix | Instead of creating one permission for each log group in the destination lambda, the code will take the prefix that you set in the parameter and create 1 permission for all of the log groups that match the prefix, for example if you will define "/aws/log/logs" than the lambda will create only 1 permission for all of your log groups that start with /aws/log/logs instead of 1 permision for each of the log group. use this parameter when you have more than 50 log groups. Pay attention that you will not see the log groups as a trigger in the lambda if you use this parameter. | n/a | |
| AWSApiRequestsLimit | In case you got an error in the lambda which is related to ThrottlingException, then you can increase the limit of the requests that the lambda can do to the AWS API using this variable. | 10 |  |
| FunctionMemorySize | The maximum allocated memory this lambda may consume. The default value is the minimum recommended setting please consult coralogix support before changing. | 1024 |  |
| FunctionTimeout | The maximum time in seconds the function may be allowed to run. The default value is the minimum recommended setting please consult coralogix support before changing. | 300 |  |
| NotificationEmail | Failure notification email address | | |

## Requirements

### Firehose

We are assuming you deployed our Firehose integration per our integration https://coralogix.com/docs/aws-firehose/

Firehose Destination requires a Role to allow Cloudwatch to send logs to Firehose. For that please verify that the role you are using in DESTINATION_ROLO has the following definitions.

Permissions policy

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "firehose:PutRecord",
                "firehose:PutRecordBatch",
                "firehose:UpdateDestination"
            ],
            "Resource": "arn:aws:firehose:sa-east-1:771039649440:deliverystream/coralogixdeliverystream-sa-east-1",
            "Effect": "Allow"
        }
    ]
}
```

Trust relationships

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CloudwatchToFirehoseRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "logs.sa-east-1.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

## License

This project is licensed under the Apache-2.0 License.
