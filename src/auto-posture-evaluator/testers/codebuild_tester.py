import time
import boto3
import interfaces
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name) -> None:
        self.aws_region = region_name
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.aws_codebuild_client = boto3.client('codebuild', region_name=region_name)
        self.codebuild_projects = []

    def declare_tested_provider(self) -> str:
        return "aws"

    def declare_tested_service(self) -> str:
        return "codebuild"

    def run_tests(self) -> list:
        all_regions = self._get_all_aws_regions()
        if any([self.aws_region == region for region in all_regions]):
            self.codebuild_projects = self._get_all_codebuild_projects()
            executor_list = []
            return_values = []

            with ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.codebuild_project_build_artifacts_should_be_encrypted))

                for future in executor_list:
                    return_values.extend(future.result())

            return return_values
        else:
            return None

    def _get_all_codebuild_projects(self):
        projects = []
        paginator = self.aws_codebuild_client.get_paginator('list_projects')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            projects.extend(page['projects'])

        return projects

    def _get_all_aws_regions(self):
        all_regions = []
        boto3_client = boto3.client('ec2', region_name='us-east-1')
        response = boto3_client.describe_regions(AllRegions=True)

        for region in response['Regions']:
            all_regions.append(region['RegionName'])

        return all_regions

    def _append_codebuild_test_results(self, item, item_type, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": item,
            "item_type": item_type,
            "test_name": test_name,
            "test_result": issue_status,
            "region_name": self.aws_region
        }

    def codebuild_project_build_artifacts_should_be_encrypted(self):
        result = []
        test_name = "aws_codebuild_project_build_output_artifacts_should_be_encrypted"

        projects = self.codebuild_projects

        if projects:
            response = self.aws_codebuild_client.batch_get_projects(names=projects)
            projects_details = response['projects']

            for project in projects_details:
                project_arn = project['arn']

                artifacts_encryption_disable = project['artifacts'].get('encryptionDisabled')

                if artifacts_encryption_disable is not None:
                    if artifacts_encryption_disable:
                        result.append(self._append_codebuild_test_results(project_arn, "aws_codebuild_project", test_name, "issue_found"))
                    else:
                        result.append(self._append_codebuild_test_results(project_arn, "aws_codebuild_project", test_name, "no_issue_found"))
                else:
                    result.append(self._append_codebuild_test_results(project_arn, "aws_codebuild_project", test_name, "no_issue_found"))
        else: pass

        return result
