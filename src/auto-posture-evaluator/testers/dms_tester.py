import concurrent.futures
import time
from datetime import timezone, datetime

import boto3
import interfaces


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_dms_client = boto3.client('dms', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.all_dms_replica_instances = []

    def declare_tested_service(self) -> str:
        return 'dms'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global' or self.region_name not in self._get_regions():
            return None
        self.all_dms_replica_instances = self._return_all_dms_replica_instances()
        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_dms_certificate_is_not_expired))
            executor_list.append(executor.submit(self.detect_dms_endpoint_should_use_ssl))
            executor_list.append(
                executor.submit(self.detect_dms_replication_instance_should_not_be_publicly_accessible))
            executor_list.append(
                executor.submit(self.detect_replication_instances_have_auto_minor_version_upgrade_enabled))
            executor_list.append(executor.submit(self.detect_multi_az_is_enabled))
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

    def _append_dms_test_result(self, dms_data, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": dms_data['ReplicationInstanceIdentifier'],
            "item_type": "dms",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _return_all_dms_replica_instances(self):
        replica_instances = []
        response = self.aws_dms_client.describe_replication_instances(MaxRecords=100)
        replica_instances.extend(response['ReplicationInstances'])
        while 'Marker' in response and response['Marker']:
            response = self.aws_dms_client.describe_replication_instances(MaxRecords=100, Marker=response['Marker'])
            replica_instances.extend(response['ReplicationInstances'])
        return replica_instances

    def _return_all_dms_certificates(self):
        dms_certificates = []
        response = self.aws_dms_client.describe_certificates(MaxRecords=100)
        dms_certificates.extend(response['Certificates'])
        while 'Marker' in response and response['Marker']:
            response = self.aws_dms_client.describe_certificates(MaxRecords=100, Marker=response['Marker'])
            dms_certificates.extend(response['Certificates'])
        return dms_certificates

    def _return_dms_certificate_status(self, test_name, issue_status):
        dms_certificate_status = []
        for dms_replica_instance_dict in self.all_dms_replica_instances:
            dms_certificate_status.append(
                self._append_dms_test_result(dms_replica_instance_dict, test_name, issue_status))
        return dms_certificate_status

    def detect_dms_endpoint_should_use_ssl(self):
        ssl_endpoint_result = []
        test_name = 'aws_dms_endpoint_should_use_ssl'
        for dms_replica_instance_dict in self.all_dms_replica_instances:
            dms_connection_response = self.aws_dms_client.describe_connections(Filters=[
                {
                    'Name': 'replication-instance-arn',
                    'Values': [dms_replica_instance_dict['ReplicationInstanceArn']]
                },
            ])
            if dms_connection_response and 'Connections' in dms_connection_response and dms_connection_response[
                'Connections']:
                for dms_connection_response_dict in dms_connection_response:
                    dms_endpoint_response = self.aws_dms_client.describe_endpoints(Filters=[
                        {
                            'Name': 'endpoint-id',
                            'Values': [dms_connection_response_dict['EndpointIdentifier']]
                        },
                    ])
                    for dms_endpoint_response_dict in dms_endpoint_response['Endpoints']:
                        if 'SslMode' in dms_endpoint_response_dict and dms_endpoint_response_dict[
                            'SslMode'].lower() == 'none':
                            ssl_endpoint_result.append(
                                self._append_dms_test_result(dms_replica_instance_dict, test_name, 'issue_found'))
                        else:
                            ssl_endpoint_result.append(
                                self._append_dms_test_result(dms_replica_instance_dict, test_name, 'no_issue_found'))

        return ssl_endpoint_result

    def detect_dms_certificate_is_not_expired(self):
        dms_certificates = self._return_all_dms_certificates()
        issue_found = False
        test_name = 'aws_dms_certificate_is_not_expired'
        if not dms_certificates:
            issue_found = True
        for dms_certificate_dict in dms_certificates:
            if datetime.now(timezone.utc) > dms_certificate_dict['ValidToDate']:
                issue_found = True
                break
        if issue_found:
            return self._return_dms_certificate_status(test_name, 'issue_found')
        else:
            return self._return_dms_certificate_status(test_name, 'no_issue_found')

    def detect_dms_replication_instance_should_not_be_publicly_accessible(self):
        dms_public_accessible = []
        test_name = 'aws_dms_replication_instance_should_not_be_publicly_accessible'
        for dms_replica_instance_dict in self.all_dms_replica_instances:
            if dms_replica_instance_dict['PubliclyAccessible']:
                dms_public_accessible.append(
                    self._append_dms_test_result(dms_replica_instance_dict, test_name, 'issue_found'))
            else:
                dms_public_accessible.append(
                    self._append_dms_test_result(dms_replica_instance_dict, test_name, 'no_issue_found'))
        return dms_public_accessible

    def detect_replication_instances_have_auto_minor_version_upgrade_enabled(self):
        test_name = "aws_dms_replication_instances_should_have_auto_minor_version_upgrade"
        result = []

        replication_instances = self.all_dms_replica_instances
        for instance in replication_instances:
            auto_minor_version_upgrade = instance['AutoMinorVersionUpgrade']

            if auto_minor_version_upgrade:
                result.append(self._append_dms_test_result(instance, test_name, "no_issue_found"))
            else:
                result.append(self._append_dms_test_result(instance, test_name, "issue_found"))

        return result

    def detect_multi_az_is_enabled(self):
        test_name = "aws_dms_replication_instance_should_use_multi_AZ_deployment"
        result = []

        replication_instances = self.all_dms_replica_instances
        for instance in replication_instances:
            multi_az = instance['MultiAZ']

            if multi_az:
                result.append(self._append_dms_test_result(instance, test_name, "no_issue_found"))
            else:
                result.append(self._append_dms_test_result(instance, test_name, "issue_found"))

        return result

