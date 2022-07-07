import time
import boto3
import interfaces
import concurrent.futures

def _return_default_port_on_redshift_engines():
    return 5439


def _return_default_custom_master_username_on_redshift_engines():
    return 'awsuser'


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_redshift_client = boto3.client('redshift', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.redshift_clusters = {}

    def declare_tested_service(self) -> str:
        return 'redshift'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global' or self.region_name not in self._get_regions():
            return None
        self.redshift_clusters = self._get_all_redshift_clusters()
        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_redshift_cluster_encrypted))
            executor_list.append(executor.submit(self.detect_redshift_cluster_not_publicly_accessible))
            executor_list.append(executor.submit(self.detect_redshift_cluster_not_using_default_port))
            executor_list.append(executor.submit(self.detect_redshift_cluster_not_using_custom_master_username))
            executor_list.append(executor.submit(self.detect_redshift_cluster_using_logging))
            executor_list.append(executor.submit(self.detect_redshift_cluster_allow_version_upgrade))
            executor_list.append(executor.submit(self.detect_redshift_cluster_requires_ssl))
            executor_list.append(executor.submit(self.detect_redshift_cluster_not_using_ec2_classic))
            executor_list.append(executor.submit(self.get_redshift_cluster_not_encrypted_with_kms))
            for future in executor_list:
                return_value += future.result()
        return return_value

    def _get_regions(self) -> list:
        region_list = []
        for page in self.ssm.get_paginator('get_parameters_by_path').paginate(
                Path='/aws/service/global-infrastructure/regions'
        ):
            for p in page['Parameters']:
                region_list.append(p['Value'])
        return region_list

    def _append_redshift_test_result(self, redshift, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": redshift['ClusterIdentifier'],
            "item_type": "redshift_cluster",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _return_redshift_logging_status(self, cluster_identifier):
        return self.aws_redshift_client.describe_logging_status(ClusterIdentifier=cluster_identifier)

    def _return_parameter_group_names(self, parameter_groups):
        result = []
        for pg in parameter_groups:
            result.append(pg['ParameterGroupName'])
        return result

    def _return_cluster_parameter_data(self, group_name):
        return self.aws_redshift_client.describe_cluster_parameters(ParameterGroupName=group_name)

    def _return_ssl_enabled_on_parameter_groups(self, params):
        ssl_enabled = False
        for pg in params:
            if pg['ParameterName'].lower() == 'require_ssl' and pg['ParameterValue'].lower() == 'true':
                ssl_enabled = True
                break
        return ssl_enabled

    def detect_redshift_cluster_encrypted(self):
        test_name = "aws_redshift_encrypted_redshift_cluster"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            if not redshift['Encrypted']:
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def detect_redshift_cluster_not_publicly_accessible(self):
        test_name = "aws_redshift_not_publicly_accessible_redshift_cluster"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            if redshift['PubliclyAccessible']:
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def detect_redshift_cluster_not_using_default_port(self):
        test_name = "aws_redshift_cluster_not_using_default_port"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            if _return_default_port_on_redshift_engines() == redshift['Endpoint']['Port']:
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def detect_redshift_cluster_not_using_custom_master_username(self):
        test_name = "aws_redshift_cluster_not_using_custom_master_username"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            if _return_default_custom_master_username_on_redshift_engines() == redshift['MasterUsername'].lower():
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def detect_redshift_cluster_using_logging(self):
        test_name = "aws_redshift_cluster_using_logging"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            logging_metadata = self._return_redshift_logging_status(redshift['ClusterIdentifier'])
            if not logging_metadata['LoggingEnabled']:
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def detect_redshift_cluster_allow_version_upgrade(self):
        test_name = "aws_redshift_cluster_allow_version_upgrade"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            if not redshift['AllowVersionUpgrade']:
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def detect_redshift_cluster_requires_ssl(self):
        test_name = "aws_redshift_cluster_requires_ssl"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            issue_found = True
            for parameter_group_name in self._return_parameter_group_names(redshift['ClusterParameterGroups']):
                param_key_value = self._return_cluster_parameter_data(parameter_group_name)
                if 'Parameters' in param_key_value and len(param_key_value['Parameters']):
                    if self._return_ssl_enabled_on_parameter_groups(param_key_value['Parameters']):
                        issue_found = False
            if not issue_found:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
        return result

    def detect_redshift_cluster_not_using_ec2_classic(self):
        test_name = "aws_redshift_cluster_not_using_ec2_classic"
        result = []
        for redshift in self.redshift_clusters['Clusters']:
            if not ('VpcId' in redshift and redshift['VpcId']):
                result.append(self._append_redshift_test_result(redshift, test_name, "issue_found"))
            else:
                result.append(self._append_redshift_test_result(redshift, test_name, "no_issue_found"))
        return result

    def get_redshift_cluster_not_encrypted_with_kms(self):
        test_name = "aws_redshift_cluster_not_encrypted_with_KMS_customer_master_keys"
        result = []

        clusters = self.redshift_clusters["Clusters"]

        for cluster in clusters:
            encrypted = cluster["Encrypted"]

            if encrypted:
                result.append(self._append_redshift_test_result(cluster, test_name, "no_issue_found"))
            else:
                result.append(self._append_redshift_test_result(cluster, test_name, "issue_found"))

        return result

    def _get_all_redshift_clusters(self):
        clusters = []
        paginator = self.aws_redshift_client.get_paginator('describe_clusters')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            clusters.extend(page['Clusters'])

        return { "Clusters" : clusters }

