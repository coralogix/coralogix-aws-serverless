import boto3
import os
import re
import uuid
import cfnresponse 
from botocore.config import Config
import logging
import sys
from typing import List, Optional, Dict, Any

logger = logging.getLogger('logger')
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

config = Config(
   retries = { 
      'max_attempts': int(os.environ.get('AWS_API_REUESTS_LIMIT', 10)),
      'mode': 'standard'
   }
)

cloudwatch_logs = boto3.client('logs', config=config)
lambda_client = boto3.client('lambda', config=config)

def lambda_handler(event: Dict[str, Any], context) -> None:
    """
    Main Lambda function handler that manages CloudWatch log group subscriptions.
    
    This function handles both CloudFormation custom resource events and CloudWatch
    log group creation events. It can:
    - Add permissions to Lambda functions for log group access
    - Scan existing log groups and add subscriptions based on regex patterns
    - Add subscription filters to new log groups that match specified patterns
    - Handle both Firehose and Lambda destinations
    
    Args:
        event: Lambda event containing either CloudFormation request or CloudWatch log group details
        context: Lambda context object containing function metadata
    
    Environment Variables:
        REGEX_PATTERN: Comma-separated regex patterns to match log group names
        DESTINATION_TYPE: Type of destination ('firehose' or 'lambda')
        LOGS_FILTER: Filter pattern for log events (optional)
        SCAN_OLD_LOGGROUPS: Whether to scan existing log groups on creation ('true'/'false')
        DESTINATION_ARN: ARN of the destination (Firehose or Lambda)
        DISABLE_ADD_PERMISSION: Whether to skip adding Lambda permissions ('true'/'false')
        ADD_PERMISSIONS_TO_ALL_LOG_GROUPS: Whether to add permissions for all log groups ('true'/'false')
        LOG_GROUP_PERMISSION_PREFIX: Comma-separated prefixes for log groups that need permissions
    """
    status = cfnresponse.SUCCESS
    try:
        regex_pattern_list     = os.environ.get('REGEX_PATTERN').split(',')
        destination_type       = os.environ.get('DESTINATION_TYPE')
        logs_filter            = os.environ.get('LOGS_FILTER', '')
        scan_old_log_groups    = os.environ.get('SCAN_OLD_LOGGROUPS', 'false')
        destination_arn        = os.environ.get('DESTINATION_ARN')
        filter_name            = 'Coralogix_Filter_' + str(uuid.uuid4())
        region                 = context.invoked_function_arn.split(":")[3]
        account_id             = context.invoked_function_arn.split(":")[4]
        disable_add_permission = os.environ.get('DISABLE_ADD_PERMISSION', 'false')
        add_permissions_to_all_log_groups = os.environ.get('ADD_PERMISSIONS_TO_ALL_LOG_GROUPS', 'false')
        log_group_permission_prefix = os.environ.get('LOG_GROUP_PERMISSION_PREFIX', '').split(',')
        
        # Handle CloudFormation Create event
        if "RequestType" in event and event['RequestType'] == 'Create':
            if disable_add_permission != 'true':
                logger.info("Adding permissions during creation")
                add_permissions_first_time(destination_arn, log_group_permission_prefix, region, account_id, add_permissions_to_all_log_groups)

            if scan_old_log_groups == 'true':
                logger.info(f"Scanning all existing log groups: {scan_old_log_groups}")
                list_log_groups_and_subscriptions(
                    cloudwatch_logs, regex_pattern_list, logs_filter, destination_arn, 
                    filter_name, context, log_group_permission_prefix, add_permissions_to_all_log_groups
                )
                update_scan_old_log_groups_status(context, lambda_client)
            elif scan_old_log_groups == 'true':
                scan_old_log_groups = 'false'
                update_scan_old_log_groups_status(context, lambda_client)

        # Handle CloudWatch log group creation events
        if scan_old_log_groups != 'true' and "RequestType" not in event:
            log_group_to_subscribe = event['detail']['requestParameters']['logGroupName']
            found_log_group_in_regex_pattern = False
            
            for regex_pattern in regex_pattern_list:
                if re.match(regex_pattern, log_group_to_subscribe):
                    if destination_type == 'firehose':
                        logger.info(f"Adding subscription filter for {log_group_to_subscribe}")
                        status = add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                        if status == cfnresponse.FAILED:
                            logger.warning(f"Retrying to add subscription filter for {log_group_to_subscribe}")
                            add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                        break
                    elif destination_type == 'lambda':
                        try:
                            if not check_if_log_group_exist_in_log_group_permission_prefix(log_group_to_subscribe, log_group_permission_prefix):
                                if disable_add_permission == 'true' or add_permissions_to_all_log_groups == 'true':
                                    logger.info("Skipping adding permission to lambda")
                                else:
                                    logger.info(f"Adding permission to lambda for {log_group_to_subscribe}")
                                    add_permission_to_lambda(destination_arn, log_group_to_subscribe, region, account_id)
                            logger.info(f"Adding subscription filter for {log_group_to_subscribe}")
                            found_log_group_in_regex_pattern = True
                        except Exception as e:
                            logger.error(f"Failed to put subscription filter for {log_group_to_subscribe}: {e}")
                            status = cfnresponse.FAILED
                        break

            if found_log_group_in_regex_pattern:
                status = add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)
                if status == cfnresponse.FAILED:
                    logger.info(f"Retrying to add subscription filter for {log_group_to_subscribe}")
                    if disable_add_permission == 'true' or add_permissions_to_all_log_groups == 'true':
                        logger.info("Skipping adding permission to lambda")
                    else:
                        add_permission_to_lambda(destination_arn, log_group_to_subscribe, region, account_id)
                    add_subscription(filter_name, logs_filter, log_group_to_subscribe, destination_arn)

    except Exception as e:
        logger.error(f"Failed with exception: {e}")
        status = cfnresponse.FAILED
    finally:
        # Send response for CloudFormation custom resource events
        if "RequestType" in event and "ResponseURL" in event:
            logger.info("Sending response to custom resource")
            cfnresponse.send(
                event,
                context,
                status,
                {},
                event.get('PhysicalResourceId', context.aws_request_id)
            )
        else:
            logger.info("Skipping cfnresponse.send — not a CloudFormation event")

def list_log_groups_and_subscriptions(
    cloudwatch_logs, 
    regex_pattern_list: List[str], 
    logs_filter: str, 
    destination_arn: str, 
    filter_name: str, 
    context, 
    log_group_permission_prefix: List[str], 
    add_permissions_to_all_log_groups: str
) -> None:
    """
    Scan all log groups in the region and add subscriptions to those matching regex patterns.
    
    This function is designed to run only once during the initial setup. It:
    - Retrieves all log groups in the region using pagination
    - Filters log groups based on provided regex patterns
    - Checks existing subscriptions to avoid duplicates
    - Adds subscription filters for matching log groups
    - Handles Lambda permissions when needed
    
    Args:
        cloudwatch_logs: Boto3 CloudWatch Logs client
        regex_pattern_list: List of regex patterns to match log group names
        logs_filter: Filter pattern for log events
        destination_arn: ARN of the destination (Firehose or Lambda)
        filter_name: Name for the subscription filter
        context: Lambda context object
        log_group_permission_prefix: List of prefixes for log groups that need permissions
        add_permissions_to_all_log_groups: Whether to add permissions for all log groups
    """
    log_groups = []
    response = {'nextToken': None}  # Initialize with a dict containing nextToken as None
    
    # Paginate through all log groups
    while response.get('nextToken') is not None or 'logGroups' not in response:
        kwargs = {}
        if 'nextToken' in response and response['nextToken'] is not None:
            kwargs['nextToken'] = response['nextToken']
        response = cloudwatch_logs.describe_log_groups(**kwargs, logGroupClass="STANDARD")
        log_groups.extend(response['logGroups'])
    
    region = context.invoked_function_arn.split(":")[3]
    account_id = context.invoked_function_arn.split(":")[4]
    
    for log_group in log_groups:
        create_subscription = False
        log_group_name = log_group['logGroupName']

        for regex_pattern in regex_pattern_list:
            if regex_pattern and re.match(regex_pattern, log_group_name):
                # Check existing subscriptions
                subscriptions = cloudwatch_logs.describe_subscription_filters(logGroupName=log_group_name)
                subscriptions = subscriptions.get('subscriptionFilters')

                if subscriptions is None:
                    create_subscription = True
                elif len(subscriptions) < 2:
                    create_subscription = True
                    for subscription in subscriptions:
                        if subscription['destinationArn'] == destination_arn:
                            create_subscription = False
                            break
                elif len(subscriptions) >= 2:
                    logger.warning(f"Skipping {log_group_name} as it already has 2 subscriptions")
                    break

                if create_subscription:
                    if identify_arn_service(destination_arn) == "lambda" and add_permissions_to_all_log_groups == 'false':
                        if not check_if_log_group_exist_in_log_group_permission_prefix(log_group_name, log_group_permission_prefix):
                            add_permission_to_lambda(destination_arn, log_group_name, region, account_id)
                        logger.info(f"Adding subscription filter for {log_group_name}")
                        status = add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                        if status == cfnresponse.FAILED:
                            logger.warning(f"Retrying to add subscription filter for {log_group_name}")
                            add_permission_to_lambda(destination_arn, log_group_name, region, account_id)
                            add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                    else:
                        logger.info(f"Adding subscription filter for {log_group_name}")
                        status = add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                        if status == cfnresponse.FAILED:
                            logger.warning(f"Retrying to add subscription filter for {log_group_name}")
                            add_subscription(filter_name, logs_filter, log_group_name, destination_arn)
                break  # no need to continue the loop if we find a match for the log group

def add_subscription(
    filter_name: str, 
    logs_filter: str, 
    log_group_to_subscribe: str, 
    destination_arn: str, 
    role_arn: Optional[str] = None
) -> str:
    """
    Add a subscription filter to a CloudWatch log group.
    
    Creates a subscription filter that forwards log events from the specified log group
    to the destination (Firehose or Lambda). The function handles both cases with and
    without IAM role ARN.
    
    Args:
        filter_name: Name for the subscription filter
        logs_filter: Filter pattern for log events (e.g., '{ $.level = "ERROR" }')
        log_group_to_subscribe: Name of the log group to subscribe
        destination_arn: ARN of the destination (Firehose or Lambda)
        role_arn: Optional IAM role ARN for cross-account access
    
    Returns:
        str: 'SUCCESS' or 'FAILED' status
    
    Raises:
        Exception: When subscription filter creation fails
    """
    try:
        subscription_params = {
            'destinationArn': destination_arn,
            'filterName': filter_name,
            'filterPattern': logs_filter,
            'logGroupName': log_group_to_subscribe,
        }
        
        if role_arn:
            subscription_params['roleArn'] = role_arn
            
        cloudwatch_logs.put_subscription_filter(**subscription_params)
        logger.info(f"Successfully put subscription filter for {log_group_to_subscribe}")
        return cfnresponse.SUCCESS
    except Exception as e:
        logger.error(f"Failed to put subscription filter for {log_group_to_subscribe}: {e}")
        return cfnresponse.FAILED

def add_permissions_first_time(
    destination_arn: str, 
    log_group_permission_prefix: List[str], 
    region: str, 
    account_id: str, 
    add_permissions_to_all_log_groups: str
) -> None:
    """
    Add initial permissions to Lambda function during first-time setup.
    
    This function is called during the CloudFormation Create event to set up
    the necessary permissions for the Lambda function to be invoked by CloudWatch Logs.
    It can either add permissions for all log groups or specific prefixes.
    
    Args:
        destination_arn: ARN of the Lambda function
        log_group_permission_prefix: List of log group prefixes that need permissions
        region: AWS region
        account_id: AWS account ID
        add_permissions_to_all_log_groups: Whether to add permissions for all log groups
    """
    logger.info("Adding permissions to the lambda on the creation of the lambda function for the first time")
    if add_permissions_to_all_log_groups == "true":
        add_permission_to_lambda(destination_arn, '*', region, account_id)
    else:
        for prefix in log_group_permission_prefix:
            add_permission_to_lambda(destination_arn, f"{prefix}*", region, account_id)

def add_permission_to_lambda(destination_arn: str, log_group_name: str, region: str, account_id: str) -> None:
    """
    Add resource-based permission to Lambda function for CloudWatch Logs invocation.
    
    Creates a resource-based policy that allows CloudWatch Logs to invoke the Lambda
    function for the specified log group. The statement ID is sanitized to contain
    only alphanumeric characters, hyphens, and underscores.
    
    Args:
        destination_arn: ARN of the Lambda function
        log_group_name: Name of the log group (can include wildcards)
        region: AWS region
        account_id: AWS account ID
    
    Raises:
        Exception: When permission addition fails
    """
    try:
        # Sanitize log group name for statement ID (only alphanumeric, hyphen, underscore)
        log_group_statement_id = re.sub(r'[^a-zA-Z0-9\-_]', '-', log_group_name)
        lambda_client.add_permission(
            FunctionName=destination_arn,
            StatementId=f'allow-trigger-from-{log_group_statement_id}',
            Action='lambda:InvokeFunction',
            Principal='logs.amazonaws.com',
            SourceArn=f'arn:aws:logs:{region}:{account_id}:log-group:{log_group_name}:*',
        )
        logger.info(f"Successfully added permission to lambda {destination_arn}, with log group name: {log_group_name}")
    except Exception as e:
        logger.error(f"Failed to add permission to lambda {destination_arn}, with log group name: {log_group_name}: {e}")

def check_if_log_group_exist_in_log_group_permission_prefix(
    log_group_name: str, 
    log_group_permission_prefix: List[str]
) -> bool:
    """
    Check if a log group name matches any of the specified permission prefixes.
    
    This function determines whether a log group is already covered by the
    permission prefixes, which helps avoid adding duplicate permissions.
    
    Args:
        log_group_name: Name of the log group to check
        log_group_permission_prefix: List of permission prefixes to check against
    
    Returns:
        bool: True if log group matches any prefix, False otherwise
    """
    if not log_group_permission_prefix or log_group_permission_prefix == ['']:
        return False
    
    for prefix in log_group_permission_prefix:
        if log_group_name.startswith(prefix):
            return True
    return False

def identify_arn_service(arn: str) -> str:
    """
    Identify the AWS service from an ARN.
    
    Parses an AWS ARN to determine which service it belongs to.
    Currently supports Lambda and Firehose services.
    
    Args:
        arn: AWS ARN to analyze
    
    Returns:
        str: Service name ('lambda', 'firehose', 'Unknown AWS Service', or 'Invalid ARN format')
    """
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

def update_scan_old_log_groups_status(context, lambda_client) -> None:
    """
    Update the Lambda function's environment variables to disable old log group scanning.
    
    This function is called after the initial scan of existing log groups to prevent
    the scan from running again on subsequent invocations. It updates the
    SCAN_OLD_LOGGROUPS environment variable to 'false'.
    
    Args:
        context: Lambda context object containing function metadata
        lambda_client: Boto3 Lambda client
    
    Raises:
        Exception: When function configuration update fails
    """
    function_name = context.function_name

    # Fetch the current function configuration
    current_config = lambda_client.get_function_configuration(FunctionName=function_name)
    current_env_vars = current_config['Environment']['Variables']

    # Update the environment variables
    current_env_vars['SCAN_OLD_LOGGROUPS'] = 'false'

    # Update the Lambda function configuration
    try:
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': current_env_vars}
        )
        logger.info(f"Successfully updated {function_name} to disable old log group scanning")
    except Exception as e:
        logger.error(f"Error updating function configuration: {e}")
