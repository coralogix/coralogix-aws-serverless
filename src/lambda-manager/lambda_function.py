import boto3
import os
import re
import uuid
import cfnresponse 
from botocore.config import Config

config = Config(
   retries = {
      'max_attempts': 10,
      'mode': 'standard'
   }
)

cloudwatch_logs = boto3.client('logs', config=config)

def lambda_handler(event, context):
    status = cfnresponse.SUCCESS
    lambda_client = boto3.client('lambda', config=config)
    try:
        regex_pattern_list  = os.environ.get('REGEX_PATTERN').split(',')
        destination_type    = os.environ.get('DESTINATION_TYPE')
        logs_filter         = os.environ.get('LOGS_FILTER', '')
        scan_all_log_groups = os.environ.get('SCAN_OLD_LOGGROUPS', 'false')
        destination_arn     = os.environ.get('DESTINATION_ARN')
        role_arn            = os.environ.get('DESTINATION_ROLE')
        filter_name         = 'Coralogix_Filter_' + str(uuid.uuid4())
        log_group_permission_prefix = os.environ.get('LOG_GROUP_PERMISSION_PREFIX', '').split(',')
        region              = context.invoked_function_arn.split(":")[3]
        account_id          = context.invoked_function_arn.split(":")[4]
        log_exist_in_regex_pattern = False

        if "RequestType" in event and event['RequestType'] == 'Create' and log_group_permission_prefix != ['']:
            print("Addning permissions in creation")
            add_permissions_first_time(destination_arn, log_group_permission_prefix, region, account_id)

        if scan_all_log_groups == 'true' and "RequestType" in event and event['RequestType'] == 'Create':
            print(f"Scanning all log groups: {scan_all_log_groups}")
            list_log_groups_and_subscriptions(cloudwatch_logs, regex_pattern_list, logs_filter, destination_arn, role_arn, filter_name, context,log_group_permission_prefix)
            update_scan_all_log_groups_status(context, lambda_client)

        elif scan_all_log_groups == 'true':
            scan_all_log_groups = 'false'
            update_scan_all_log_groups_status(context, lambda_client)

        if scan_all_log_groups != 'true' and "RequestType" not in event:
            log_group_to_subscribe = event['detail']['requestParameters']['logGroupName']
            print(f"Log Group: {log_group_to_subscribe}")
            for regex_pattern in regex_pattern_list:
                if regex_pattern and re.match(regex_pattern, log_group_to_subscribe):
                    log_exist_in_regex_pattern = True
                    if destination_type == 'firehose':
                        print(f"Adding subscription filter for {log_group_to_subscribe}")
                        status = add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                        if status == cfnresponse.FAILED:
                            print(f"retrying to add subscription filter for {log_group_to_subscribe}")
                            add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                    elif destination_type == 'lambda':
                        try:
                            if not check_if_log_group_exist_in_log_group_permission_prefix(log_group_to_subscribe, log_group_permission_prefix):
                                print("Adding permission to lambda")
                                add_permission_to_lambda(destination_arn, log_group_to_subscribe, region, account_id)
                            print(f"Adding subscription filter for {log_group_to_subscribe}")
                            status = add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                            if status == cfnresponse.FAILED:
                                print(f"retrying to add subscription filter for {log_group_to_subscribe}")
                                add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                        except Exception as e:
                            print(f"Failed to put subscription filter for {log_group_to_subscribe}: {e}")
                            status = cfnresponse.FAILED
                    else:
                        print(f"Invalid destination type {destination_type}")
                        status = cfnresponse.FAILED

            if not log_exist_in_regex_pattern:
                print(f"Loggroup {log_group_to_subscribe} excluded")
    except Exception as e:
        print(f"Failed with exception: {e}")
        status = cfnresponse.FAILED
    finally:
        if "RequestType" in event:
            print("Sending response to custom resource")
            cfnresponse.send(
                event,
                context,
                status,
                {},
                event.get('PhysicalResourceId', context.aws_request_id)
            )

def list_log_groups_and_subscriptions(cloudwatch_logs, regex_pattern_list, logs_filter, destination_arn, role_arn, filter_name, context,log_group_permission_prefix):
    '''Scan for all of the log groups in the region and add subscription to the log groups that match the regex pattern, this function will only run 1 time'''
    log_groups = []
    response = {'nextToken': None}  # Initialize with a dict containing nextToken as None
    print("Scanning all log groups")
    while response.get('nextToken') is not None or 'logGroups' not in response:
        kwargs = {}
        if 'nextToken' in response and response['nextToken'] is not None:
            kwargs['nextToken'] = response['nextToken']
        response = cloudwatch_logs.describe_log_groups(**kwargs)
        log_groups.extend(response['logGroups'])
    region = context.invoked_function_arn.split(":")[3]
    account_id = context.invoked_function_arn.split(":")[4]
    for log_group in log_groups:
        create_subscription = False
        log_group_name = log_group['logGroupName']

        for regex_pattern in regex_pattern_list:
            if regex_pattern and re.match(regex_pattern, log_group_name):

                subscriptions = cloudwatch_logs.describe_subscription_filters(logGroupName=log_group_name)
                subscriptions = subscriptions.get('subscriptionFilters')

                if subscriptions == None:
                    create_subscription = True

                elif len(subscriptions) < 2:
                    create_subscription = True
                    for subscription in subscriptions:
                        if subscription['destinationArn'] == destination_arn:
                            print(f"  Subscription already exists for {log_group_name}")
                            create_subscription = False
                            break

                elif len(subscriptions) >= 2:
                    print(f"  Skipping {log_group_name} as it already has 2 subscriptions")
                    continue

                if create_subscription:
                        print(f"Log Group: {log_group_name}")
                        if identify_arn_service(destination_arn) == "lambda":
                            if not check_if_log_group_exist_in_log_group_permission_prefix(log_group_name, log_group_permission_prefix):
                                add_permission_to_lambda(destination_arn, log_group_name, region, account_id)
                            print(f"Adding subscription filter for {log_group_name}")
                            status = add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                            if status == cfnresponse.FAILED:
                                print(f"retrying to add subscription filter for {log_group_name}")
                                add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                        else:
                            print(f"Adding subscription filter for {log_group_name}")
                            status = add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                            if status == cfnresponse.FAILED:
                                print(f"retrying to add subscription filter for {log_group_name}")
                                add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                break # no need to continue the loop if we find a match for the log group

def add_subscription(filter_name: str, logs_filter: str, log_group_to_subscribe: str, destination_arn: str, role_arn: str = None) -> str:
    '''Add subscription to CloudWatch log group'''
    try:
        if role_arn is None:
            cloudwatch_logs.put_subscription_filter(
                destinationArn=destination_arn,
                filterName= filter_name,
                filterPattern=logs_filter,
                logGroupName=log_group_to_subscribe,
            )
        else:
            cloudwatch_logs.put_subscription_filter(
                destinationArn=destination_arn,
                roleArn=role_arn,
                filterName= filter_name,
                filterPattern=logs_filter,
                logGroupName=log_group_to_subscribe,
            )
        return cfnresponse.SUCCESS
    except Exception as e:
        print(f"Failed to put subscription filter for {log_group_to_subscribe}: {e}")
        return cfnresponse.FAILED

def add_permissions_first_time(destination_arn: str, log_group_permission_prefix: list[str], region: str, account_id: str):
    '''Add permissions to the lambda on the creation of the lambda function for the first time'''
    lambda_client   = boto3.client('lambda', config=config)
    for prefix in log_group_permission_prefix:
        try:
            lambda_client.add_permission(
                FunctionName=destination_arn,
                StatementId=f'allow-trigger-from-{prefix.replace("/","")}-log-groups',
                Action='lambda:InvokeFunction',
                Principal='logs.amazonaws.com',
                SourceArn=f'arn:aws:logs:{region}:{account_id}:log-group:{prefix}*:*',
            )
        except Exception as e:
            print(f"Failed to add permission {prefix}: {e}")

def add_permission_to_lambda(destination_arn: str, log_group_name: str, region: str, account_id: str):
    '''In case that the log group is not part of the log_group_permission_prefix then add permissions for it to the lambda function'''
    lambda_client   = boto3.client('lambda', config=config)
    try:
        lambda_client.add_permission(
            FunctionName=destination_arn,
            StatementId=f'allow-trigger-from-{log_group_name.replace('/','')}',
            Action='lambda:InvokeFunction',
            Principal='logs.amazonaws.com',
            SourceArn=f'arn:aws:logs:{region}:{account_id}:log-group:{log_group_name}:*',
        )
    except Exception as e:
        print(f"Failed to add permission to lambda {destination_arn}: {e}")

def check_if_log_group_exist_in_log_group_permission_prefix(log_group_name: str, log_group_permission_prefix: str) -> bool:
    '''Check if the log group is part of the log_group_permission_prefix'''
    if log_group_permission_prefix == ['']:
        return False
    for prefix in log_group_permission_prefix:
        if log_group_name.startswith(prefix):
            return True
    return False

def identify_arn_service(arn: str) -> str:
    arn_parts = arn.split(':')
    if len(arn_parts) < 6:
        return "Invalid ARN format"
    service = arn_parts[2]
    if service == "lambda":
        return "lambda"
    elif service == "firehose":
        return "firehose"
    else:
        return "Unknown AWS Service"

def update_scan_all_log_groups_status(context, lambda_client):

    function_name = context.function_name

    # Fetch the current function configuration
    current_config = lambda_client.get_function_configuration(FunctionName=function_name)
    current_env_vars = current_config['Environment']['Variables']

    # Update the environment variables
    current_env_vars['SCAN_OLD_LOGGROUPS'] = 'false'

    # Update the Lambda function configuration
    try:
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': current_env_vars}
        )
        print("Updated environment variables:", response['Environment']['Variables'])
    except Exception as e:
        print("Error updating function configuration:", e)
        status = cfnresponse.FAILED