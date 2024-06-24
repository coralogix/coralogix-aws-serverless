import boto3
import os
import re
import uuid
import cfnresponse 

def identify_arn_service(arn):
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

def list_log_groups_and_subscriptions(cloudwatch_logs, regex_pattern, logs_filter, destination_arn, role_arn, filter_name, context):
    log_groups = []
    response = {'nextToken': None}  # Initialize with a dict containing nextToken as None
    print("Scanning all log groups")
    while response.get('nextToken') is not None or 'logGroups' not in response:
        kwargs = {}
        if 'nextToken' in response and response['nextToken'] is not None:
            kwargs['nextToken'] = response['nextToken']
        response = cloudwatch_logs.describe_log_groups(**kwargs)
        log_groups.extend(response['logGroups'])
    for log_group in log_groups:
        log_group_name = log_group['logGroupName']
        if regex_pattern and re.match(regex_pattern, log_group_name):
            print(f"Log Group: {log_group_name}")

            subscriptions = cloudwatch_logs.describe_subscription_filters(logGroupName=log_group_name)
            subscriptions = subscriptions.get('subscriptionFilters')
            print(f" Subscriptions: {subscriptions} for {log_group_name}")
            print(f" Subscriptions length: {len(subscriptions)} for {log_group_name}")
            if subscriptions is None or len(subscriptions) == 0:
                print(f"  No subscriptions found for {log_group_name}")
                destination_type = identify_arn_service(destination_arn)
                print(f"  Subscribing {log_group_name} to {destination_type} {destination_arn}")
                if destination_type == 'firehose':
                    try:
                        cloudwatch_logs.put_subscription_filter(
                            destinationArn=destination_arn,
                            roleArn=role_arn,
                            filterName= filter_name,
                            filterPattern=logs_filter,
                            logGroupName=log_group_name,
                        )
                    except Exception as e:
                        print(f"Failed to put subscription filter for {log_group_name}: {e}")
                        continue
                elif destination_type == 'lambda':
                    try:
                        lambda_client = boto3.client('lambda')
                        region = context.invoked_function_arn.split(":")[3]
                        account_id = context.invoked_function_arn.split(":")[4]
                        lambda_client.add_permission(
                          FunctionName=destination_arn,
                          StatementId=f'allow-trigger-from-{log_group_name}',
                          Action='lambda:InvokeFunction',
                          Principal='logs.amazonaws.com',
                          SourceArn=f'arn:aws:logs:{region}:{account_id}:log-group:{log_group_name}:*',
                        )
                        cloudwatch_logs.put_subscription_filter(
                            destinationArn=destination_arn,
                            filterName= "coralogix-aws-shipper-cloudwatch-trigger",
                            filterPattern=logs_filter,
                            logGroupName=log_group_name,
                        )
                    except Exception as e:
                        print(f"Failed to put subscription filter for {log_group_name}: {e}")
                        continue
                else:
                    print(f"Invalid destination type {destination_type}")
            for subscription in subscriptions:
                print(f" subscription length {len(subscriptions)}")
                print(f" subscription arn {subscription['destinationArn']}")
                if subscription['destinationArn'] == destination_arn:
                    print(f"  Subscription already exists for {log_group_name}")
                    continue
                if len(subscriptions) == 2:
                    print(f"  Subscriptions limit for {log_group_name}")
                    print(f" subscription length {len(subscriptions)}")
                    continue

                destination_type = identify_arn_service(destination_arn)
                print(f"  Subscribing {log_group_name} to {destination_type} {destination_arn}")
                if destination_type == 'firehose':
                    try:
                        cloudwatch_logs.put_subscription_filter(
                            destinationArn=destination_arn,
                            roleArn=role_arn,
                            filterName= filter_name,
                            filterPattern=logs_filter,
                            logGroupName=log_group_name,
                        )
                    except Exception as e:
                        print(f"Failed to put subscription filter for {log_group_name}: {e}")
                        continue
                elif destination_type == 'lambda':
                    try:
                        lambda_client = boto3.client('lambda')
                        region = context.invoked_function_arn.split(":")[3]
                        account_id = context.invoked_function_arn.split(":")[4]
                        lambda_client.add_permission(
                          FunctionName=destination_arn,
                          StatementId=f'allow-trigger-from-{log_group_name}',
                          Action='lambda:InvokeFunction',
                          Principal='logs.amazonaws.com',
                          SourceArn=f'arn:aws:logs:{region}:{account_id}:log-group:{log_group_name}:*',
                        )
                        cloudwatch_logs.put_subscription_filter(
                            destinationArn=destination_arn,
                            filterName= "coralogix-aws-shipper-cloudwatch-trigger",
                            filterPattern=logs_filter,
                            logGroupName=log_group_name,
                        )
                    except Exception as e:
                        print(f"Failed to put subscription filter for {log_group_name}: {e}")
                        continue
                else:
                    print(f"Invalid destination type {destination_type}")

def lambda_handler(event, context):
    status = cfnresponse.SUCCESS
    try:
        cloudwatch_logs     = boto3.client('logs')
        regex_pattern       = os.environ.get('REGEX_PATTERN')
        destination_type    = os.environ.get('DESTINATION_TYPE')
        logs_filter         = os.environ.get('LOGS_FILTER', '')
        scan_all_log_groups = os.environ.get('SCAN_OLD_LOGGROUPS', 'false')
        destination_arn     = os.environ.get('DESTINATION_ARN')
        role_arn            = os.environ.get('DESTINATION_ROLE')
        filter_name         = 'Coralogix_Filter_' + str(uuid.uuid4())

        print(f"Scanning all log groups: {scan_all_log_groups}")
        if scan_all_log_groups == 'true' and "RequestType" in event:
            list_log_groups_and_subscriptions(cloudwatch_logs, regex_pattern, logs_filter, destination_arn, role_arn, filter_name, context)
            lambda_client = boto3.client('lambda')
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
        elif scan_all_log_groups != 'true' and "RequestType" not in event:
            log_group_to_subscribe = event['detail']['requestParameters']['logGroupName']
            print(f"Log Group: {log_group_to_subscribe}")
            if regex_pattern and re.match(regex_pattern, log_group_to_subscribe):
                if destination_type == 'firehose':
                        try:
                            cloudwatch_logs.put_subscription_filter(
                                destinationArn=destination_arn,
                                roleArn=role_arn,
                                filterName= filter_name,
                                filterPattern=logs_filter,
                                logGroupName=log_group_to_subscribe,
                            )
                        except Exception as e:
                            print(f"Failed to put subscription filter for {log_group_to_subscribe}: {e}")
                            status = cfnresponse.FAILED
                elif destination_type == 'lambda':
                    try:
                        lambda_client = boto3.client('lambda')
                        region = context.invoked_function_arn.split(":")[3]
                        account_id = context.invoked_function_arn.split(":")[4]
                        lambda_client.add_permission(
                          FunctionName=destination_arn,
                          StatementId=f'allow-trigger-from-{log_group_to_subscribe}',
                          Action='lambda:InvokeFunction',
                          Principal='logs.amazonaws.com',
                          SourceArn=f'arn:aws:logs:{region}:{account_id}:log-group:{log_group_to_subscribe}:*',
                        )
                        cloudwatch_logs.put_subscription_filter(
                            destinationArn=destination_arn,
                            filterName= "coralogix-aws-shipper-cloudwatch-trigger",
                            filterPattern=logs_filter,
                            logGroupName=log_group_to_subscribe,
                        )
                    except Exception as e:
                        print(f"Failed to put subscription filter for {log_group_to_subscribe}: {e}")
                        status = cfnresponse.FAILED
                else:
                    print(f"Invalid destination type {destination_type}")
                    status = cfnresponse.FAILED
            else:
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
