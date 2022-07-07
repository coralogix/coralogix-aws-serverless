import time
import interfaces
import boto3
import botocore.exceptions
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.aws_region = region_name
        self.aws_cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
        self.aws_cloudformation_client = boto3.client('cloudformation', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')

    def declare_tested_service(self) -> str:
        return 'cloudwatch'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        all_regions = self._get_all_aws_regions()
        if any([self.aws_region == region for region in all_regions]):
            executor_list = []
            return_values = []

            with ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.get_unauthorized_api_calls_not_monitored))
                executor_list.append(executor.submit(self.get_route_table_changes_not_monitored))
                executor_list.append(executor.submit(self.get_console_sign_in_failure_alarm))
                executor_list.append(executor.submit(self.get_s3_bucket_policy_changes_not_monitored))
                executor_list.append(executor.submit(self.get_vpc_changes_not_monitored))
                executor_list.append(executor.submit(self.get_organization_changes_not_monitored))
                executor_list.append(executor.submit(self.get_usage_of_root_account_not_monitored))
                executor_list.append(executor.submit(self.get_cloudtrail_configuration_changes_not_monitored))
                executor_list.append(executor.submit(self.get_management_console_sign_in_without_mfa_not_monitored))
                executor_list.append(executor.submit(self.get_cmk_configuration_change_not_monitored))
                executor_list.append(executor.submit(self.get_network_gateway_changes_not_monitored))
                executor_list.append(executor.submit(self.get_security_group_changes_not_monitored))
                executor_list.append(executor.submit(self.get_network_acl_changes_not_monitored))
                executor_list.append(executor.submit(self.get_aws_config_configuration_changes_not_monitored))
                executor_list.append(executor.submit(self.get_iam_policy_changes_not_monitored))
                executor_list.append(executor.submit(self.get_enable_aws_cloudformation_stack_notifications))

                for future in executor_list:
                    return_values.extend(future.result())

            return return_values
        else:
            return None

    def _get_result(self, item, item_type, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": item,
            "item_type": item_type,
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.aws_region
        }

    def _get_all_aws_regions(self):
        all_regions = []
        boto_client = boto3.client('ec2', region_name='us-east-1')
        response = boto_client.describe_regions(AllRegions=True)

        for region in response['Regions']:
            all_regions.append(region['RegionName'])

        return all_regions

    def get_unauthorized_api_calls_not_monitored(self):
        test_name = "aws_cloudwatch_unauthorized_api_calls_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='SecurityGroupEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("SecurityGroupEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("SecurityGroupEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_route_table_changes_not_monitored(self):
        test_name = "aws_cloudwatch_route_table_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='RouteTableEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("RouteTableEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("RouteTableEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_console_sign_in_failure_alarm(self):
        test_name = "aws_cloudwatch_console_sign_in_failure_alarm"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='ConsoleSignInFailureCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("ConsoleSignInFailureCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("ConsoleSignInFailureCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_s3_bucket_policy_changes_not_monitored(self):
        test_name = "aws_cloudwatch_s3_bucket_policy_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='S3BucketEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("S3BucketEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("S3BucketEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_vpc_changes_not_monitored(self):
        test_name = "aws_cloudwatch_vpc_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='VpcEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("VpcEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("VpcEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_organization_changes_not_monitored(self):
        test_name = "aws_cloudwatch_organization_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='OrganizationEvents', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("OrganizationEvents", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("OrganizationEvents", "cloudwatch_alarm", test_name, "issue_found")]

    def get_usage_of_root_account_not_monitored(self):
        test_name = "aws_cloudwatch_usage_of_root_account_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='RootAccountUsageEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("RootAccountUsageEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("RootAccountUsageEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_cloudtrail_configuration_changes_not_monitored(self):
        test_name = "aws_cloudwatch_cloudtrail_configuration_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='CloudTrailEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("CloudTrailEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("CloudTrailEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_management_console_sign_in_without_mfa_not_monitored(self):
        test_name = "aws_cloudwatch_management_console_sign_in_without_mfa_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='ConsoleSignInWithoutMfaCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("ConsoleSignInWithoutMfaCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("ConsoleSignInWithoutMfaCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_cmk_configuration_change_not_monitored(self):
        test_name = "aws_cloudwatch_cmk_configuration_change_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='CMKEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("CMKEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("CMKEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_network_gateway_changes_not_monitored(self):
        test_name = "aws_cloudwatch_network_gateway_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='GatewayEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("GatewayEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("GatewayEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_security_group_changes_not_monitored(self):
        test_name = "aws_cloudwatch_security_group_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='SecurityGroupEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("SecurityGroupEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("SecurityGroupEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_network_acl_changes_not_monitored(self):
        test_name = "aws_cloudwatch_network_acl_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='NetworkAclEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("NetworkAclEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("NetworkAclEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_aws_config_configuration_changes_not_monitored(self):
        test_name = "aws_cloudwatch_configuration_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='ConfigEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("ConfigEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("ConfigEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_iam_policy_changes_not_monitored(self):
        test_name = "aws_cloudwatch_iam_policy_changes_not_monitored"
        alarms = self.aws_cloudwatch_client.describe_alarms_for_metric(MetricName='IAMPolicyEventCount', Namespace='CloudTrailMetrics')
        if len(alarms['MetricAlarms']) > 0:
            return [self._get_result("IAMPolicyEventCount", "cloudwatch_alarm", test_name, "no_issue_found")]
        else:
            return [self._get_result("IAMPolicyEventCount", "cloudwatch_alarm", test_name, "issue_found")]

    def get_enable_aws_cloudformation_stack_notifications(self):
        test_name = "aws_cloudwatch_enable_aws_cloudformation_stack_notifications"
        stacks = self.aws_cloudformation_client.list_stacks()
        result = []
        for stack in stacks['StackSummaries']:
            stack_name = stack['StackName']
            issue_detected = False
            try:
                stack_info = self.aws_cloudformation_client.describe_stacks(StackName=stack_name)
                notif_arns = stack_info['Stacks'][0]['NotificationARNs']
                if not notif_arns or len(notif_arns) == 0:
                    issue_detected = True
            except botocore.exceptions.ClientError as ex:
                if ex.response['Error']['Code'] == 'ValidationError':
                    issue_detected = True
                else:
                    raise ex

            if issue_detected:
                self._get_result(stack_name, "cloudformation_stack", test_name, "issue_found")
            else:
                self._get_result(stack_name, "cloudformation_stack", test_name, "no_issue_found")

        return result
