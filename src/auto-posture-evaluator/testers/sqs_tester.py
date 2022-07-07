import time
import boto3
import interfaces
import json, re
import concurrent.futures

def _format_string_to_json(text):
    return json.loads(text)


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_sqs_client = boto3.client('sqs', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')

    def declare_tested_service(self) -> str:
        return 'sqs'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global' or self.region_name not in self._get_regions():
            return None

        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_sqs_server_side_encryption))
            executor_list.append(executor.submit(self.detect_sqs_public_accessible_queues))
            executor_list.append(executor.submit(self.detect_sqs_not_encrypted_with_kms_customer_master_keys))
            executor_list.append(executor.submit(self.detect_sqs_cross_account_access))
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

    def _append_sqs_test_result(self, sqs_url, test_name, issue_status) -> dict:
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": sqs_url,
            "item_type": "sqs",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _return_all_the_sqs(self):
        response = self.aws_sqs_client.list_queues(MaxResults=100)
        sqs_urls = []
        if 'QueueUrls' not in response:
            return []
        sqs_urls.extend(response['QueueUrls'])
        # The API returns max of 100 topic arns in one call \
        # and need to paginate it using the next token sent.
        while 'NextToken' in response and response['NextToken']:
            response = self.aws_sqs_client.list_queues(NextToken=response['NextToken'])
            sqs_urls.extend(response['QueueUrls'])
        return sqs_urls

    def _return_all_dead_letter_sqs(self, queue_url):
        try:
            response = self.aws_sqs_client.client.list_dead_letter_source_queues(QueueUrl=queue_url, MaxResults=100)
            sqs_dead_letter_urls = []
            if 'queueUrls' not in response:
                return []
            sqs_dead_letter_urls.extend(response['queueUrls'])
            # The API returns max of 100 topic arns in one call \
            # and need to paginate it using the next token sent.
            while 'NextToken' in response and response['NextToken']:
                response = self.aws_sqs_client.list_queues(NextToken=response['NextToken'])
                sqs_dead_letter_urls.extend(response['QueueUrls'])
            return sqs_dead_letter_urls
        except:
            return []

    def _find_sse_for_all_queues(self, queue_url, test_name):
        result = []
        get_queue_attributes_result = self.aws_sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['SqsManagedSseEnabled', 'KmsMasterKeyId'])
        if 'Attributes' in get_queue_attributes_result and ('SqsManagedSseEnabled' in \
                                                            get_queue_attributes_result['Attributes'] and
                                                            get_queue_attributes_result['Attributes'][
                                                                'SqsManagedSseEnabled'] == 'true') or (
                'KmsMasterKeyId' in get_queue_attributes_result['Attributes'] and
                get_queue_attributes_result['Attributes'][
                    'KmsMasterKeyId']):
            result.append(self._append_sqs_test_result(queue_url, test_name, "no_issue_found"))
        else:
            result.append(self._append_sqs_test_result(queue_url, test_name, "issue_found"))
        return result

    def _get_all_public_accessibility_for_all_queues(self, queue_url, test_name):
        result = []
        get_attribute_result = self.aws_sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['Policy'])
        policy_dict = _format_string_to_json(get_attribute_result['Attributes']['Policy'])
        restricted = True
        for policy_statement_dict in policy_dict['Statement']:
            if policy_statement_dict['Effect'] == 'Allow':
                if 'Principal' in policy_statement_dict and 'AWS' in policy_statement_dict['Principal'] and \
                        policy_statement_dict['Principal'][
                            'AWS'] == '*' and 'Condition' not in policy_statement_dict:
                    restricted = False
                    break
                if 'Effect' in policy_statement_dict and policy_statement_dict['Effect'] == 'Deny':
                    continue
        if restricted:
            result.append(self._append_sqs_test_result(queue_url, test_name, "no_issue_found"))
        else:
            result.append(self._append_sqs_test_result(queue_url, test_name, "issue_found"))
        return result

    def _get_sse_enabled_and_disabled_queue(self, queue_result_dict) -> list:
        result = []
        test_name = "aws_sqs_has_server_side_encryption"
        for queue_url in queue_result_dict:
            result.extend(self._find_sse_for_all_queues(queue_url, test_name))
            for dl_queue_url in self._return_all_dead_letter_sqs(queue_url):
                result.extend(self._find_sse_for_all_queues(dl_queue_url, test_name))
        return result

    def _get_policy_for_queues(self, queue_result_dict) -> list:
        result = []
        test_name = "aws_sqs_public_accessibility"
        for queue_url in queue_result_dict:
            result.extend(self._get_all_public_accessibility_for_all_queues(queue_url, test_name))
            for dl_queue_url in self._return_all_dead_letter_sqs(queue_url):
                result.extend(self._get_all_public_accessibility_for_all_queues(dl_queue_url, test_name))
        return result

    def detect_sqs_server_side_encryption(self) -> list:
        return self._get_sse_enabled_and_disabled_queue(self._return_all_the_sqs())

    def detect_sqs_public_accessible_queues(self) -> list:
        return self._get_policy_for_queues(self._return_all_the_sqs())

    def detect_sqs_cross_account_access(self) -> list:
        result = []
        test_name = 'aws_sqs_cross_account_access'
        client_organizations = boto3.client('organizations')
        try:
            resp = client_organizations.list_accounts()
            all_account_obj = ['Accounts'] in resp and resp['Accounts'] or []
            all_accounts = []
            for accounts_dict in all_account_obj:
                all_accounts.append(accounts_dict)
            if not all_accounts:
                all_accounts = [self.account_id]
        except:
            all_accounts = [self.account_id]

        for queue_url in self._return_all_the_sqs():
            response = self.aws_sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['Policy'])
            issue_found = False
            if 'Attributes' in response and response['Attributes'] and 'Policy' in response['Attributes']:
                policy_dict = _format_string_to_json(response['Attributes']['Policy'])
                if 'Statement' in policy_dict and policy_dict['Statement']:
                    for statement_dict in policy_dict['Statement']:
                        if 'Principal' in statement_dict and (statement_dict['Principal'] == '*' or 'AWS' in statement_dict['Principal'] and statement_dict['Principal']['AWS'] == '*'):
                            issue_found = True
                        if issue_found:
                            break
                        if 'AWS' in statement_dict['Principal']:
                            if isinstance(statement_dict['Principal']['AWS'], str):
                                account_id_to_compare = (
                                    re.search(r'\b\d{12}\b', statement_dict['Principal']['AWS'])).group(0)
                                if account_id_to_compare not in all_accounts:
                                    issue_found = True
                                    break
                                continue
                            for aws_account_info in statement_dict['Principal']['AWS']:
                                try:
                                    account_id_to_compare = (re.search(r'\b\d{12}\b', aws_account_info)).group(0)
                                    if account_id_to_compare not in all_accounts:
                                        issue_found = True
                                        break
                                except:
                                    pass
            if issue_found:
                result.append(self._append_sqs_test_result(queue_url, test_name, "issue_found"))
            else:
                result.append(self._append_sqs_test_result(queue_url, test_name, "no_issue_found"))
        return result

    def detect_sqs_not_encrypted_with_kms_customer_master_keys(self):
        result = []
        test_name = 'aws_sqs_not_encrypted_with_kms_customer_master_keys'
        for queue_url in self._return_all_the_sqs():
            response = self.aws_sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['KmsMasterKeyId'])
            if 'Attributes' in response and response['Attributes'] and 'KmsMasterKeyId' in response['Attributes'] and \
                    response['Attributes']['KmsMasterKeyId']:
                result.append(self._append_sqs_test_result(queue_url, test_name, "no_issue_found"))
            else:
                result.append(self._append_sqs_test_result(queue_url, test_name, "issue_found"))
        return result

