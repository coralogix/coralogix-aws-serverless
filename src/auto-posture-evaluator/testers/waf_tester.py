import concurrent.futures
import time

import boto3
import interfaces


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_waf_client = None
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.scope = None
        self.web_acls = []

    def declare_tested_service(self) -> str:
        return 'waf'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global':
            '''If region is global by default we have to consider region name as us-east-1.
               All the web acls will lie in us-east-1 for the CLOUDFRONT'''
            self.region_name = 'us-east-1'
            self.aws_waf_client = boto3.client('wafv2', region_name=self.region_name)
            self.scope = 'CLOUDFRONT'
            self.web_acls = self._return_all_web_acls(self.scope)
            waf_dict = self._get_all_rule_sets(self.scope, self.aws_waf_client, self.web_acls)
        elif self.region_name in self._get_regions():
            self.aws_waf_client = boto3.client('wafv2', region_name=self.region_name)
            self.scope = 'REGIONAL'
            self.web_acls = self._return_all_web_acls(self.scope)
            waf_dict = self._get_all_rule_sets(self.scope, self.aws_waf_client, self.web_acls)
        else:
            return None
        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(
                executor.submit(self.detect_aws_managed_rules_known_bad_inputs_ruleset, self.scope, waf_dict))
            executor_list.append(
                executor.submit(self.detect_aws_managed_rule_group_anonymous_ip_list, self.scope, waf_dict))

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

    def _append_waf_test_result(self, waf, test_name, issue_status) -> dict:
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": waf,
            "item_type": "waf",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _return_web_acls_based_on_scope(self, scope, waf_client) -> list:
        web_acls = []
        response = waf_client.list_web_acls(Scope=scope, Limit=100)
        if 'WebACLs' in response and response['WebACLs']:
            web_acls.extend(response['WebACLs'])
        while 'NextMarker' in response and response['NextMarker']:
            response = waf_client.list_web_acls(Scope=scope, Limit=100,
                                                NextMarker=response['NextMarker'])
            web_acls.extend(response['WebACLs'])
        return web_acls

    def _return_all_web_acls(self, scope):
        all_web_acls = self._return_web_acls_based_on_scope(scope, self.aws_waf_client)
        return all_web_acls

    def _get_all_rule_sets(self, scope, client, web_acls) -> list:
        result = []
        for web_acl in web_acls:
            response = client.get_web_acl(
                Name=web_acl['Name'],
                Scope=scope,
                Id=web_acl['Id']
            )
            result.append(response['WebACL'])
        return result

    def _find_waf_issues(self, scope, issue_type, waf_acls, test_name) -> list:
        result = []
        for value in waf_acls:
            if 'Rules' in value and value['Rules']:
                issue_found = True
                for rule in value['Rules']:
                    if rule['Name'] == issue_type:
                        issue_found = False
                        break
                if issue_found:
                    result.append(self._append_waf_test_result(value["Name"] + '@@' + scope, test_name, 'issue_found'))
                else:
                    result.append(
                        self._append_waf_test_result(value["Name"] + '@@' + scope, test_name, 'no_issue_found'))

            else:
                result.append(self._append_waf_test_result(value["Name"] + '@@' + scope, test_name, 'issue_found'))

        return result

    def detect_aws_managed_rules_known_bad_inputs_ruleset(self, scope, _waf_rules) -> list:
        rule_type_to_check = 'AWS-AWSManagedRulesKnownBadInputsRuleSet'
        test_name = 'aws_waf_web_acl_should_include_aws_managed_rules_against_log4shell'
        _waf_result = self._find_waf_issues(scope, rule_type_to_check, _waf_rules, test_name)
        return _waf_result

    def detect_aws_managed_rule_group_anonymous_ip_list(self, scope, _waf_rules) -> list:
        rule_type_to_check = 'AWS-AWSManagedRulesAnonymousIpList'
        test_name = 'aws_waf_web_acl_should_include_managed_rule_group_anonymous_ip_list'
        _waf_result_li = self._find_waf_issues(scope, rule_type_to_check, _waf_rules, test_name)

        return _waf_result_li

