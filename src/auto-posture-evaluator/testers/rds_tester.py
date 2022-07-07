import boto3
import concurrent.futures
import interfaces
import time
from datetime import datetime, timezone


def _return_default_port_on_rds_engines(db_engine):
    if 'mysql' in db_engine.lower() or 'aurora' in db_engine.lower() or 'maria' in db_engine.lower():
        return 3306
    elif 'postgres' in db_engine.lower():
        return 5432
    elif 'oracle' in db_engine.lower():
        return 1521
    elif 'sql' in db_engine.lower():
        return 1433
    return


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_rds_client = boto3.client('rds', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.rds_instances = []
        self.rds_snapshots = []

    def declare_tested_service(self) -> str:
        return 'rds'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global' or self.region_name not in self._get_regions():
            return None
        self.rds_instances = self.aws_rds_client.describe_db_instances()
        self.rds_snapshots = self.aws_rds_client.describe_db_snapshots()

        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_rds_instance_encrypted))
            executor_list.append(executor.submit(self.detect_rds_instance_not_publicly_accessible))
            executor_list.append(executor.submit(self.detect_rds_instance_not_using_default_port))
            executor_list.append(executor.submit(self.detect_rds_snapshot_not_publicly_accessible))
            executor_list.append(executor.submit(self.detect_rds_backup_retention_period_less_than_a_week))
            executor_list.append(
                executor.submit(self.detect_rds_instance_should_have_automatic_minor_version_upgrades_enabled))
            executor_list.append(executor.submit(self.detect_rds_instance_should_have_automated_backups_enabled))
            executor_list.append(executor.submit(self.detect_rds_transport_encryption_disabled))
            executor_list.append(executor.submit(self.detect_rds_public_cluster_manual_snapshots))
            executor_list.append(executor.submit(self.detect_rds_instance_level_events_subscriptions))
            executor_list.append(executor.submit(self.detect_rds_last_restorable_time_check_more_than_a_week_old))

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

    def _append_rds_test_result(self, rds, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": rds['DBInstanceIdentifier'],
            "item_type": "rds_db_instance",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _append_rds_snap_test_result(self, rds, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": rds['DBSnapshotIdentifier'],
            "item_type": "rds_snapshot",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _fetch_snapshot_metadata(self, snapshot_identifier):
        return self.aws_rds_client.describe_db_snapshot_attributes(DBSnapshotIdentifier=snapshot_identifier)

    def detect_rds_instance_encrypted(self):
        test_name = "aws_rds_encrypted_rds_db_instances"
        result = []
        for rds in self.rds_instances['DBInstances']:
            if not rds['StorageEncrypted']:
                result.append(self._append_rds_test_result(rds, test_name, "issue_found"))
            else:
                result.append(self._append_rds_test_result(rds, test_name, "no_issue_found"))
        return result

    def detect_rds_instance_not_publicly_accessible(self):
        test_name = "aws_rds_not_publicly_accessible_rds_db_instances"
        result = []
        for rds in self.rds_instances['DBInstances']:
            if rds['PubliclyAccessible']:
                result.append(self._append_rds_test_result(rds, test_name, "issue_found"))
            else:
                result.append(self._append_rds_test_result(rds, test_name, "no_issue_found"))
        return result

    def detect_rds_instance_not_using_default_port(self):
        test_name = "aws_rds_db_instances_not_using_default_port"
        result = []
        for rds in self.rds_instances['DBInstances']:
            default_db_engine_port = _return_default_port_on_rds_engines(rds['Engine'])
            if 'Endpoint' in rds and 'Port' in rds['Endpoint'] and default_db_engine_port == rds['Endpoint']['Port']:
                result.append(self._append_rds_test_result(rds, test_name, "issue_found"))
            else:
                result.append(self._append_rds_test_result(rds, test_name, "no_issue_found"))
        return result

    def detect_rds_snapshot_not_publicly_accessible(self):
        test_name = "aws_rds_snapshot_not_publicly_accessible"
        result = []
        for rds_snap in self.rds_snapshots['DBSnapshots']:
            issue_found = False
            snap_metadata = self._fetch_snapshot_metadata(rds_snap['DBSnapshotIdentifier'])
            for snap_meta in snap_metadata['DBSnapshotAttributesResult']['DBSnapshotAttributes']:
                if snap_meta['AttributeName'] == 'restore' and 'all' in snap_meta['AttributeValues']:
                    result.append(self._append_rds_snap_test_result(rds_snap, test_name, "issue_found"))
                    issue_found = True
            if not issue_found:
                result.append(self._append_rds_snap_test_result(rds_snap, test_name, "no_issue_found"))
        return result

    def detect_rds_backup_retention_period_less_than_a_week(self):
        result = []
        test_name = "aws_rds_backup_retention_period_less_than_a_week"
        for rds_instance in self.rds_instances['DBInstances']:
            if 'BackupRetentionPeriod' in rds_instance and rds_instance[
                'BackupRetentionPeriod'] >= 7:
                result.append(self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))
            else:
                result.append(self._append_rds_test_result(rds_instance, test_name, "issue_found"))
        return result

    def detect_rds_instance_should_have_automatic_minor_version_upgrades_enabled(self):
        result = []
        test_name = "aws_rds_instance_should_have_automatic_minor_version_upgrades_enabled"
        for rds_instance in self.rds_instances['DBInstances']:
            if 'AutoMinorVersionUpgrade' in rds_instance and rds_instance[
                'AutoMinorVersionUpgrade']:
                result.append(self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))
            else:
                result.append(self._append_rds_test_result(rds_instance, test_name, "issue_found"))
        return result

    def detect_rds_instance_should_have_automated_backups_enabled(self):
        result = []
        test_name = "aws_rds_instance_should_have_automated_backups_enabled"
        for rds_instance in self.rds_instances['DBInstances']:
            if 'BackupRetentionPeriod' in rds_instance and rds_instance[
                'BackupRetentionPeriod'] > 0:
                result.append(self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))
            else:
                result.append(self._append_rds_test_result(rds_instance, test_name, "issue_found"))
        return result

    def detect_rds_transport_encryption_disabled(self):
        result = []
        test_name = "aws_rds_transport_encryption_disabled"
        for rds_instance in self.rds_instances['DBInstances']:
            issue_found = True
            for db_parameter_dict in rds_instance['DBParameterGroups']:
                if 'DBParameterGroupName' in db_parameter_dict and db_parameter_dict['DBParameterGroupName']:
                    if not issue_found:
                        break
                    response = self.aws_rds_client.describe_db_parameters(
                        DBParameterGroupName=db_parameter_dict['DBParameterGroupName'])
                    if response and 'Parameters' in response and response['Parameters']:
                        for parameter_dict in response['Parameters']:
                            if not issue_found:
                                break
                            if 'DBParameterGroupName' in parameter_dict and parameter_dict[
                                'DBParameterGroupName'] == 'rds.force_ssl' and 'ParameterValue' in parameter_dict and str(
                                parameter_dict['ParameterValue']) != '0':
                                issue_found = False
                                break
            if issue_found:
                result.append(self._append_rds_test_result(rds_instance, test_name, "issue_found"))
            else:
                result.append(self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))

        return result

    def detect_rds_public_cluster_manual_snapshots(self):
        result = []
        test_name = "aws_rds_public_cluster_manual_snapshots"
        for rds_instance in self.rds_instances['DBInstances']:
            response = self.aws_rds_client.describe_db_snapshots(
                DBInstanceIdentifier=rds_instance['DBInstanceIdentifier'],
                SnapshotType='manual')
            issue_found = False
            if 'DBSnapshots' in response and response['DBSnapshots']:
                for db_snapshot_dict in response['DBSnapshots']:
                    snapshot_attributes_response = self.aws_rds_client.describe_db_snapshot_attributes(
                        DBSnapshotIdentifier=db_snapshot_dict['DBSnapshotIdentifier'])
                    if 'DBSnapshotAttributesResult' in snapshot_attributes_response and 'DBSnapshotAttributes' in \
                            snapshot_attributes_response['DBSnapshotAttributesResult']:
                        for snapshot_attributes_response_dict in \
                                snapshot_attributes_response['DBSnapshotAttributesResult']['DBSnapshotAttributes']:
                            if 'AttributeName' in snapshot_attributes_response_dict and \
                                    snapshot_attributes_response_dict[
                                        'AttributeName'] == 'restore' and 'AttributeValues' in snapshot_attributes_response_dict and \
                                    snapshot_attributes_response_dict['AttributeValues'] and \
                                    snapshot_attributes_response_dict['AttributeValues'][0] == 'all':
                                issue_found = True
            if issue_found:
                result.append(self._append_rds_test_result(rds_instance, test_name, "issue_found"))
            else:
                result.append(self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))
        return result

    def detect_rds_instance_level_events_subscriptions(self):
        result = []
        test_name = "aws_rds_instance_level_events_subscriptions"
        event_subscription_response = self.aws_rds_client.describe_event_subscriptions()
        subscribed_db_instances = []
        is_all_instance_subscribed = False
        for event_subscription_response_dict in event_subscription_response['EventSubscriptionsList']:
            if event_subscription_response_dict['SourceType'] == 'db-instance':
                if 'SourceIdsList' in event_subscription_response_dict and event_subscription_response_dict[
                    'SourceIdsList']:
                    subscribed_db_instances.extend(event_subscription_response_dict['SourceIdsList'])
                else:
                    is_all_instance_subscribed = True
                    break
        for rds_instance in self.rds_instances['DBInstances']:
            if is_all_instance_subscribed or rds_instance['DBInstanceIdentifier'] in subscribed_db_instances:
                result.append(
                    self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))
            else:
                result.append(
                    self._append_rds_test_result(rds_instance, test_name, "issue_found"))
        return result

    def detect_rds_last_restorable_time_check_more_than_a_week_old(self):
        result = []
        test_name = "aws_rds_last_restorable_time_check_more_than_a_week_old"
        for rds_instance in self.rds_instances['DBInstances']:
            if 'LatestRestorableTime' in rds_instance and rds_instance['LatestRestorableTime'] and (
                    (datetime.now(timezone.utc) - rds_instance['LatestRestorableTime']).days) < 7:
                result.append(self._append_rds_test_result(rds_instance, test_name, "issue_found"))
            else:
                result.append(self._append_rds_test_result(rds_instance, test_name, "no_issue_found"))
        return result

