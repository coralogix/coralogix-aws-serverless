import time
import boto3
import interfaces
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name='global'):
        self.region_name = region_name
        self.aws_cloudtrail_client = boto3.client('cloudtrail')
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.all_cloudtrail_details = []

    def declare_tested_service(self) -> str:
        return 'cloudtrail'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name != 'global':
            return None
        self.all_cloudtrail_details = self._list_all_cloudtrail()

        executor_list = []
        return_values = []

        with ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_not_integrated_with_cloudwatch))
            executor_list.append(executor.submit(self.detect_not_encrypted_with_sse_kms))
            executor_list.append(executor.submit(self.detect_global_service))
            executor_list.append(executor.submit(self.detect_log_validation))
            executor_list.append(executor.submit(self.detect_multi_region_trails))

            for future in executor_list:
                return_values.extend(future.result())

        return return_values

    def _list_all_cloudtrail(self):
        response = self.aws_cloudtrail_client.list_trails()
        if not response['Trails']:
            return []
        cloud_trail = response['Trails']
        while 'NextToken' in response and response['NextToken']:
            response = self.aws_cloudtrail_client.list_trails(
                NextToken=response['NextToken'])
            cloud_trail.extend(response['Trails'])
        return cloud_trail

    def _append_cloudtrail_test_result(self, cloudtrail, test_name, issue_status) -> dict:
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": cloudtrail,
            "item_type": "cloudtrail",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def detect_not_encrypted_with_sse_kms(self):
        result = []
        test_name = 'aws_cloudtrail_not_encrypted_with_sse_kms'
        for cloud_trail_dict in self.all_cloudtrail_details:
            response = self.aws_cloudtrail_client.describe_trails(
                trailNameList=[
                    cloud_trail_dict['TrailARN']
                ],
            )
            for trail_list_dict in response['trailList']:
                if 'KmsKeyId' in trail_list_dict and trail_list_dict['KmsKeyId']:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'no_issue_found'))
                else:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'issue_found'))
        return result

    def detect_not_integrated_with_cloudwatch(self):
        result = []
        test_name = 'aws_cloudtrail_not_integrated_with_cloudwatch'
        for cloud_trail_dict in self.all_cloudtrail_details:
            response = self.aws_cloudtrail_client.describe_trails(
                trailNameList=[
                    cloud_trail_dict['TrailARN']
                ],
            )
            for trail_list_dict in response['trailList']:
                if 'CloudWatchLogsLogGroupArn' in trail_list_dict and trail_list_dict['CloudWatchLogsLogGroupArn']:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'no_issue_found'))
                else:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'issue_found'))
        return result

    def detect_global_service(self):
        result = []
        test_name = 'aws_cloudtrail_global_services_are_enabled'
        for cloud_trail_dict in self.all_cloudtrail_details:
            response = self.aws_cloudtrail_client.describe_trails(
                trailNameList=[
                    cloud_trail_dict['TrailARN']
                ],
            )
            for trail_list_dict in response['trailList']:
                if 'IncludeGlobalServiceEvents' in trail_list_dict and trail_list_dict['IncludeGlobalServiceEvents']:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'no_issue_found'))
                else:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'issue_found'))
        return result

    def detect_log_validation(self):
        result = []
        test_name = 'aws_cloudtrail_log_file_validation_is_enabled'
        for cloud_trail_dict in self.all_cloudtrail_details:
            response = self.aws_cloudtrail_client.describe_trails(
                trailNameList=[
                    cloud_trail_dict['TrailARN']
                ],
            )
            for trail_list_dict in response['trailList']:
                if 'LogFileValidationEnabled' in trail_list_dict and trail_list_dict['LogFileValidationEnabled']:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'no_issue_found'))
                else:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'issue_found'))
        return result

    def detect_multi_region_trails(self):
        result = []
        test_name = 'aws_cloudtrail_multi_region_is_enabled'
        for cloud_trail_dict in self.all_cloudtrail_details:
            response = self.aws_cloudtrail_client.describe_trails(
                trailNameList=[
                    cloud_trail_dict['TrailARN']
                ],
            )
            for trail_list_dict in response['trailList']:
                if 'IsMultiRegionTrail' in trail_list_dict and trail_list_dict['IsMultiRegionTrail']:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'no_issue_found'))
                else:
                    result.append(
                        self._append_cloudtrail_test_result(trail_list_dict['TrailARN'],
                                                            test_name,
                                                            'issue_found'))
        return result

