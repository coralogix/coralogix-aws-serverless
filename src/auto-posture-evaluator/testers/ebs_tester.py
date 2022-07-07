import time
from typing import List
import boto3
import interfaces
import datetime as dt
from datetime import datetime
import os
import concurrent.futures


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name: str) -> None:
        self.aws_region = region_name
        self.aws_ec2_client = boto3.client('ec2', region_name=region_name)
        self.aws_ec2_resource = boto3.resource('ec2', region_name=region_name)
        self.aws_kms_client = boto3.client('kms', region_name=region_name)
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.ebs_volumes = []

    def declare_tested_service(self) -> str:
        return 'ebs'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        all_regions = self._get_all_aws_regions()

        if any([self.aws_region == region for region in all_regions]):
            self.ebs_volumes = self._get_ebs_volumes()
            executor_list = []
            return_value = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.get_volume_is_not_encrypted, self.ebs_volumes))
                executor_list.append(executor.submit(self.get_volume_attached_to_ec2, self.ebs_volumes))
                executor_list.append(executor.submit(self.get_volume_does_not_have_recent_snapshots, self.ebs_volumes))
                executor_list.append(
                    executor.submit(self.get_volume_not_encrypted_with_kms_customer_keys, self.ebs_volumes))
                executor_list.append(executor.submit(self.get_volume_snapshots_are_public))
                for future in executor_list:
                    return_value += future.result()
            return return_value
        else:
            return None

    def _append_ebs_test_result(self, item, item_type, test_name, issue_status):
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
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        response = ec2_client.describe_regions(AllRegions=True)

        for i in response['Regions']:
            all_regions.append(i['RegionName'])

        return all_regions

    def _get_ebs_volumes(self):
        volumes = []
        can_paginate = self.aws_ec2_client.can_paginate('describe_volumes')

        if can_paginate:
            paginator = self.aws_ec2_client.get_paginator('describe_volumes')
            response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50})
            for page in response_iterator:
                volumes.extend(page['Volumes'])
        else:
            response = self.aws_ec2_client.describe_volumes()
            volumes.extend(response['Volumes'])
        return volumes

    def get_volume_is_not_encrypted(self, volumes) -> List:
        result = []
        test_name = "aws_ebs_volume_is_not_encrypted"

        for volume in volumes:
            volume_id = volume['VolumeId']
            if not volume['Encrypted']:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "issue_found"))
            else:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "no_issue_found"))

        return result

    def get_volume_attached_to_ec2(self, volumes):
        result = []
        test_name = "aws_ebs_volume_attached_to_ec2"

        for volume in volumes:
            volume_id = volume['VolumeId']
            attachments = volume['Attachments']
            if len(attachments) > 0:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "issue_found"))
            else:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "no_issue_found"))

        return result

    def get_volume_does_not_have_recent_snapshots(self, volumes):
        result = []
        test_name = "aws_ebs_volume_does_not_have_recent_snapshots"

        for volume in volumes:
            snapshots = []
            volume_id = volume['VolumeId']
            can_paginate_snapshot = self.aws_ec2_client.can_paginate('describe_snapshots')
            if can_paginate_snapshot:
                paginator_snap = self.aws_ec2_client.get_paginator('describe_snapshots')
                snap_response_iterator = paginator_snap.paginate(PaginationConfig={'PageSize': 50},
                                                                 Filters=[{'Name': 'volume-id', 'Values': [volume_id]}])
                for page in snap_response_iterator:
                    snapshots.extend(page['Snapshots'])
            else:
                snap_response = self.aws_ec2_client.describe_snapshots(
                    Filters=[{'Name': 'volume-id', 'Values': [volume_id]}])
                snapshots.extend(snap_response['Snapshots'])
            recent_snapshot_found = False
            for snapshot in snapshots:
                if snapshot['State'] != 'completed': pass
                create_date = snapshot['StartTime']
                current_date = datetime.now(tz=dt.timezone.utc)
                time_diff = (current_date - create_date).days
                if time_diff < os.environ.get('THRESHOLD', 7):
                    recent_snapshot_found = True
                    break
            if recent_snapshot_found:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "no_issue_found"))
            else:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "issue_found"))
        return result

    def get_volume_not_encrypted_with_kms_customer_keys(self, volumes):
        result = []
        test_name = "aws_ebs_volume_not_encrypted_with_kms_customer_keys"

        for volume in volumes:
            volume_id = volume['VolumeId']
            if not volume['Encrypted'] or not volume['KmsKeyId']:
                result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "issue_found"))
            else:
                key_id = volume['KmsKeyId']
                kms_response = self.aws_kms_client.list_aliases(KeyId=key_id)
                issue_found = False
                for alias in kms_response['Aliases']:
                    if alias['AliasName'] == 'alias/aws/ebs':
                        issue_found = True
                        break
                if not issue_found:
                    result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "no_issue_found"))
                else:
                    result.append(self._append_ebs_test_result(volume_id, "ebs_volume", test_name, "issue_found"))
        return result

    def get_volume_snapshots_are_public(self):
        test_name = "aws_ebs_volume_snapshots_are_public"
        result = []
        snapshots = self.aws_ec2_client.describe_snapshots(OwnerIds=[self.account_id],
                                                           Filters=[{"Name": "status", "Values": ["completed"]}])

        for snapshot in snapshots["Snapshots"]:
            snapshot_id = snapshot["SnapshotId"]
            attrs = self.aws_ec2_client.describe_snapshot_attribute(SnapshotId=snapshot_id,
                                                                    Attribute="createVolumePermission")
            if any([attr.get("Group", "") == "all" for attr in attrs["CreateVolumePermissions"]]):
                result.append(self._append_ebs_test_result(snapshot_id, "ebs_snapshot", test_name, "issue_found"))
            else:
                result.append(self._append_ebs_test_result(snapshot_id, "ebs_snapshot", test_name, "no_issue_found"))

        return result
