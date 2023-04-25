import boto3
import os
import re

def lambda_handler(event, context):
    cloudwatch_logs = boto3.client('logs')
    log_group_to_subscribe = event['detail']['requestParameters']['logGroupName']
    print("The name of Log Group to subscribe ::",log_group_to_subscribe)
    
    regex_pattern = os.environ.get('REGEX_PATTERN')
    logs_filter = os.environ.get('LOGS_FILTER', '?REPORT ?"Task timed out" ?"Process exited before completing" ?errorMessage ?"module initialization error:" ?"Unable to import module" ?"ERROR Invoke Error" ?"EPSAGON_TRACE:"')
    if regex_pattern and re.match(regex_pattern, log_group_to_subscribe):
        FIREHOSE_ARN = os.environ.get('FIREHOSE_ARN')
        ROLE_ARN = os.environ.get('FIREHOSE_ROLE')
        FILTER_NAME = 'Coralogix_Filter'
        LOG_GROUP = log_group_to_subscribe

        # Create a subscription filter
        cloudwatch_logs.put_subscription_filter(
            destinationArn=FIREHOSE_ARN,
            roleArn=ROLE_ARN,
            filterName= FILTER_NAME,
            filterPattern=logs_filter,
            logGroupName=LOG_GROUP,
        )
    else:
        print(f"Loggroup {log_group_to_subscribe} excluded")
