import time
import boto3
import interfaces
import json
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name) -> None:
        self.aws_region = region_name
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.aws_emr_client = boto3.client('emr', region_name=region_name)
        self.aws_kms_client = boto3.client('kms', region_name=region_name)
        self.emr_clusters = []

    def declare_tested_provider(self) -> str:
        return "aws"

    def declare_tested_service(self) -> str:
        return "emr"

    def run_tests(self) -> list:
        all_regions = self._get_all_aws_regions()

        if any([self.aws_region == region for region in all_regions]):
            self.emr_clusters = self._get_all_emr_clusters()
            executor_list = []
            return_values = []

            with ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.emr_cluster_should_have_a_security_configuration))
                executor_list.append(executor.submit(self.emr_cluster_should_use_kerberos_authentication))
                executor_list.append(executor.submit(self.emr_in_transit_and_at_rest_encryption_enabled))
                executor_list.append(executor.submit(self.emr_cluster_should_use_kms_for_s3_sse))
                executor_list.append(executor.submit(self.emr_cluster_should_upload_logs_to_s3))
                executor_list.append(executor.submit(self.emr_cluster_should_have_local_disk_encryption))
                executor_list.append(executor.submit(self.emr_cluster_should_have_encryption_in_transit_enabled))
                executor_list.append(executor.submit(self.emr_cluster_should_use_kms_for_s3_cse))
                executor_list.append(executor.submit(self.emr_cluster_encryption_should_be_enabled))

                for future in executor_list:
                    return_values.extend(future.result())

            return return_values
        else:
            return None

    def _get_all_aws_regions(self):
        all_regions = []
        boto3_client = boto3.client('ec2', region_name='us-east-1')
        response = boto3_client.describe_regions(AllRegions=True)

        for i in response['Regions']:
            all_regions.append(i['RegionName'])

        return all_regions

    def _get_all_emr_clusters(self):
        clusters = []
        paginator = self.aws_emr_client.get_paginator('list_clusters')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            clusters.extend(page['Clusters'])

        return clusters

    def _append_emr_cluster_test_result(self, item, item_type, test_name, issue_status):
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

    def emr_cluster_should_have_a_security_configuration(self):
        result = []
        test_name = "aws_emr_cluster_should_have_a_security_configuration"

        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response['Cluster']
                security_config = cluster_info.get("SecurityConfiguration")

                if security_config is not None:
                    result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                else:
                    result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))

        return result

    def emr_cluster_should_use_kerberos_authentication(self):
        result = []
        test_name = "aws_emr_cluster_should_use_keberos_authentication"

        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response['Cluster']

                kerberos_attrs = cluster_info.get('KerberosAttributes')

                if kerberos_attrs is not None:
                    result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                else:
                    result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))

        return result

    def emr_in_transit_and_at_rest_encryption_enabled(self):
        result = []
        test_name = "aws_emr_in_transit_and_at_rest_encryption_enabled"

        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response['Cluster']

                security_conf = cluster_info.get('SecurityConfiguration')

                if security_conf is not None:
                    result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                else:
                    result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))

        return result

    def emr_cluster_should_use_kms_for_s3_sse(self):
        result = []
        test_name = "aws_emr_cluster_should_use_kms_for_s3_sse"

        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response["Cluster"]
                security_conf = cluster_info.get("SecurityConfiguration")

                if security_conf is not None:
                    response = self.aws_emr_client.describe_security_configuration(Name=security_conf)
                    security_conf_json = response['SecurityConfiguration']
                    security_conf_obj = json.loads(security_conf_json)
                    encryption_conf = security_conf_obj.get("EncryptionConfiguration")
                    if encryption_conf is not None:
                        at_rest_encrypt_config = encryption_conf.get("AtRestEncryptionConfiguration")
                        if at_rest_encrypt_config is not None:
                            s3_encrypt_config = at_rest_encrypt_config.get("S3EncryptionConfiguration")
                            if s3_encrypt_config is not None:
                                encryption_mode = s3_encrypt_config.get("EncryptionMode")
                                if encryption_mode is not None:
                                    if encryption_mode == "SSE-KMS":
                                        result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                                    else:
                                        result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))
                                else: pass
                            else: pass
                        else: pass
                    else: pass
                else: pass
        return result

    def emr_cluster_should_have_local_disk_encryption_with_cmk(self):
        test_name = "aws_emr_cluster_should_have_local_disk_encryption_with_cmk"
        result = []

        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            issue_found = False
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response["Cluster"]
                security_conf = cluster_info.get("SecurityConfiguration")

                if security_conf is not None:
                    security_conf = self.aws_emr_client.describe_security_configuration(Name=security_conf)
                    security_conf_json = response['SecurityConfiguration']
                    security_conf_obj = json.loads(security_conf_json)
                    encryption_conf = security_conf_obj.get("EncryptionConfiguration")

                    if encryption_conf is not None:
                        at_rest_encryption_conf = encryption_conf.get("AtRestEncryptionConfiguration")
                        if at_rest_encryption_conf is not None:
                            local_disk_encryption_conf = at_rest_encryption_conf.get("LocalDiskEncryptionConfiguration")
                            if local_disk_encryption_conf is not None:
                                kms_key = local_disk_encryption_conf.get("AwsKmsKey")
                                if kms_key:
                                    kms_response = self.aws_kms_client.list_aliases(KeyId=kms_key)
                                    for alias in kms_response['Aliases']:
                                        if alias['AliasName'] == 'alias/aws/emr':
                                            issue_found = True
                                            break
                                else:
                                    issue_found = True
                            else: pass
                        else: pass
                    else: pass
                else: pass
            if issue_found:
                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))
            else:
                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
        return result

    def emr_cluster_should_upload_logs_to_s3(self):
        result = []
        test_name = "aws_emr_cluster_should_upload_logs_to_s3"

        clusters = self.emr_clusters

        for cluster in clusters:
            cluster_id = cluster['Id']
            response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
            cluster_obj = response['Cluster']

            log_uri = cluster_obj.get("LogUri")

            if log_uri is not None:
                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
            else:
                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))

        return result

    def emr_cluster_should_have_local_disk_encryption(self):
        test_name = "aws_emr_cluster_should_have_local_disk_encryption"
        result = []

        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response["Cluster"]
                security_conf = cluster_info.get("SecurityConfiguration")

                if security_conf is not None:
                    security_conf = self.aws_emr_client.describe_security_configuration(Name=security_conf)
                    security_conf_json = response['SecurityConfiguration']
                    security_conf_obj = json.loads(security_conf_json)
                    encryption_conf = security_conf_obj.get("EncryptionConfiguration")

                    if encryption_conf is not None:
                        at_rest_encryption_conf = encryption_conf.get("AtRestEncryptionConfiguration")
                        if at_rest_encryption_conf is not None:
                            local_disk_encryption_conf = at_rest_encryption_conf.get("LocalDiskEncryptionConfiguration")
                            if local_disk_encryption_conf is not None:
                                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                            else:
                                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                        else: pass
                    else: pass
                else: pass
        return result

    def emr_cluster_should_have_encryption_in_transit_enabled(self):
        test_name = "aws_emr_cluster_should_have_encryption_in_transit_enabled"
        result = []
        clusters = self._get_all_emr_clusters()

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response["Cluster"]
                security_conf = cluster_info.get("SecurityConfiguration")

                if security_conf is not None:
                    security_conf = self.aws_emr_client.describe_security_configuration(Name=security_conf)
                    security_conf_json = response['SecurityConfiguration']
                    security_conf_obj = json.loads(security_conf_json)
                    encryption_conf = security_conf_obj.get("EncryptionConfiguration")

                    if encryption_conf is not None:
                        encryption_enabled = encryption_conf.get("EnableInTransitEncryption")
                        if encryption_enabled is not None:
                            if encryption_enabled:
                                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                            else:
                                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))
                        else: pass
                    else: pass
                else: pass
        return result

    def emr_cluster_should_use_kms_for_s3_cse(self):
        result = []
        test_name = "aws_emr_cluster_should_use_kms_for_s3_cse"

        clusters = self.emr_clusters

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)

                cluster_info = response["Cluster"]
                security_conf = cluster_info.get("SecurityConfiguration")

                if security_conf is not None:
                    response = self.aws_emr_client.describe_security_configuration(Name=security_conf)
                    security_conf_json = response['SecurityConfiguration']
                    security_conf_obj = json.loads(security_conf_json)
                    encryption_conf = security_conf_obj.get("EncryptionConfiguration")
                    if encryption_conf is not None:
                        at_rest_encrypt_config = encryption_conf.get("AtRestEncryptionConfiguration")
                        if at_rest_encrypt_config is not None:
                            s3_encrypt_config = at_rest_encrypt_config.get("S3EncryptionConfiguration")
                            if s3_encrypt_config is not None:
                                encryption_mode = s3_encrypt_config.get("EncryptionMode")
                                if encryption_mode is not None:
                                    if encryption_mode == "CSE-KMS":
                                        result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                                    else:
                                        result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))
                                else: pass
                            else: pass
                        else: pass
                    else: pass
                else: pass

        return result

    def emr_cluster_encryption_should_be_enabled(self):
        result = []
        test_name = "aws_emr_cluster_encryption_should_be_enabled"

        clusters = self.emr_clusters

        for cluster in clusters:
            cluster_id = cluster['Id']
            cluster_state = cluster['Status']['State']

            if cluster_state == "TERMINATING" or cluster_state == "TERMINATED" or cluster_state == "TERMINATED_WITH_ERRORS": pass
            else:
                response = self.aws_emr_client.describe_cluster(ClusterId=cluster_id)
                cluster_info = response["Cluster"]
                security_conf = cluster_info.get("SecurityConfiguration")

                if security_conf is not None:
                    response = self.aws_emr_client.describe_security_configuration(Name=security_conf)
                    security_conf_json = response['SecurityConfiguration']
                    security_conf_obj = json.loads(security_conf_json)
                    encryption_conf = security_conf_obj.get("EncryptionConfiguration")

                    if encryption_conf is not None:
                        in_transit_encryption = encryption_conf.get("EnableInTransitEncryption")
                        at_rest_encryption = encryption_conf.get("EnableAtRestEncryption")

                        if in_transit_encryption is not None and at_rest_encryption is not None:
                            if in_transit_encryption and at_rest_encryption:
                                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "no_issue_found"))
                            else:
                                result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))
                        else: pass
                    else: pass
                else: result.append(self._append_emr_cluster_test_result(cluster_id, "emr_cluster", test_name, "issue_found"))
        return result
