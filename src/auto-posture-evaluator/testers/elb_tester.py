import os
from datetime import datetime
import time
from typing import Dict, List
import interfaces
import boto3
import jmespath
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name) -> None:
        self.aws_region = region_name
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.aws_elbs_client = boto3.client('elb', region_name=region_name)
        self.aws_elbsv2_client = boto3.client('elbv2', region_name=region_name)
        self.elbs = []
        self.elbsv2 = []
        self.cipher_suites = self._get_cipher_suite_details()
        self.latest_security_policies = self._get_aws_latest_security_policies()
        self.aws_acm_client = boto3.client('acm')
        self.aws_iam_client = boto3.client('iam')
        self.ssl_certificate_age = os.environ.get('AUTOPOSTURE_ALB_SSL_CERTIFICATE_AGE')
        self.elb_ssl_certificate_expiry = os.environ.get('AUTOPOSTURE_ELB_SSL_CERTIFICATE_EXPIRY')
        self.elb_ssl_certificate_renew = os.environ.get('AUTOPOSTURE_ELB_SSL_CERTIFICATE_ADVANCE_RENEW')

    def declare_tested_service(self) -> str:
        return "elb"

    def declare_tested_provider(self) -> str:
        return "aws"

    def run_tests(self) -> list:
        all_aws_regions = self._get_all_aws_regions()
        if any([self.aws_region == region for region in all_aws_regions]):
            self.elbs = self._get_all_elb()
            self.elbsv2 = self._get_all_elbv2()
            executor_list = []
            return_values = []

            with ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.get_elbv2_internet_facing))
                executor_list.append(executor.submit(self.get_elbv2_generating_access_log))
                executor_list.append(executor.submit(self.get_alb_using_secure_listener))
                executor_list.append(executor.submit(self.get_elb_generating_access_log))
                executor_list.append(executor.submit(self.get_elb_listeners_using_tls))
                executor_list.append(executor.submit(self.get_elb_listeners_securely_configured))
                executor_list.append(executor.submit(self.get_elb_has_secure_ssl_protocol))
                executor_list.append(executor.submit(self.get_elb_security_policy_secure_ciphers))
                executor_list.append(executor.submit(self.get_elbv2_using_latest_security_policy))
                executor_list.append(executor.submit(self.get_elbv2_has_deletion_protection))
                executor_list.append(executor.submit(self.get_elbv2_allows_https_traffic_only))
                executor_list.append(executor.submit(self.get_alb_using_tls12_or_higher))
                executor_list.append(executor.submit(self.get_nlb_using_tls12_or_higher))
                executor_list.append(executor.submit(self.get_elb_internet_facing))
                executor_list.append(executor.submit(self.get_nlb_support_insecure_negotiation_policy))
                executor_list.append(executor.submit(self.get_alb_certificate_should_be_renewed))
                executor_list.append(executor.submit(self.get_elb_cross_zone_load_balancing_enabled))
                executor_list.append(executor.submit(self.get_elb_connection_draining_enabled))
                executor_list.append(executor.submit(self.get_no_registered_instances_in_an_elbv1))
                executor_list.append(executor.submit(self.get_elb_should_allow_tlsv12_or_higher))
                executor_list.append(executor.submit(self.get_elb_ssl_certificate_expires_in_90_days))
                executor_list.append(executor.submit(self.get_elb_ssl_certificate_should_be_renewed_five_days_in_advance))
                executor_list.append(executor.submit(self.get_elb_supports_vulnerable_negotiation_policy))

                for future in executor_list:
                    return_values.extend(future.result())

            return return_values
        else:
            return None

    def _get_all_aws_regions(self):
        regions = []
        response = boto3.client('ec2', region_name='us-east-1').describe_regions(AllRegions=True)
        for region in response['Regions']:
            regions.append(region['RegionName'])
        return regions

    def _get_all_elbv2(self) -> List:
        elbs = []
        paginator = self.aws_elbsv2_client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            elbs.extend(page['LoadBalancers'])

        return elbs

    def _get_all_elb(self) -> List:
        elbs = []
        paginator = self.aws_elbs_client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            elbs.extend(page['LoadBalancerDescriptions'])

        return elbs

    def _get_aws_latest_security_policies(self) -> List:
        policies = ['ELBSecurityPolicy-2016-08', 'ELBSecurityPolicy-FS-2018-06']
        return policies

    def _get_cipher_suite_details(self) -> Dict:
        cipher_suites = {
            'AES128-GCM-SHA256': 'weak', 'ECDHE-ECDSA-AES256-SHA': 'weak', 'ECDHE-ECDSA-AES256-GCM-SHA384': 'recommended', 'AES128-SHA': 'weak',
            'ECDHE-RSA-AES128-SHA': 'weak', 'ECDHE-ECDSA-AES128-SHA256': 'weak', 'ECDHE-RSA-AES128-GCM-SHA256': 'secure', 'ECDHE-RSA-AES256-SHA384': 'weak',
            'AES256-GCM-SHA384': 'weak', 'ECDHE-RSA-AES128-SHA256': 'weak', 'AES256-SHA256': 'weak', 'ECDHE-ECDSA-AES256-SHA384': 'weak',
            'AES128-SHA256': 'weak', 'ECDHE-RSA-AES256-GCM-SHA384': 'secure', 'ECDHE-ECDSA-AES128-SHA': 'weak', 'AES256-SHA': 'weak',
            'ECDHE-ECDSA-AES128-GCM-SHA256': 'recommended', 'ECDHE-RSA-AES256-SHA': 'weak', 'DHE-RSA-AES128-SHA': 'weak',
            'DHE-DSS-AES128-SHA': 'weak', 'CAMELLIA128-SHA': 'weak', 'EDH-RSA-DES-CBC3-SHA': 'weak', 'DES-CBC3-SHA': 'weak', 'ECDHE-RSA-RC4-SHA': 'weak',
            'RC4-SHA': 'weak', 'ECDHE-ECDSA-RC4-SHA': 'weak', 'DHE-DSS-AES256-GCM-SHA384': 'recommended', 'DHE-RSA-AES256-GCM-SHA384': 'secure', 'DHE-RSA-AES256-SHA256': 'weak',
            'DHE-DSS-AES256-SHA256': 'weak', 'DHE-RSA-AES256-SHA': 'weak', 'DHE-DSS-AES256-SHA': 'weak', 'DHE-RSA-CAMELLIA256-SHA': 'weak', 'DHE-DSS-CAMELLIA256-SHA': 'weak',
            'CAMELLIA256-SHA': 'weak', 'EDH-DSS-DES-CBC3-SHA': 'weak', 'DHE-DSS-AES128-GCM-SHA256': 'recommended', 'DHE-RSA-AES128-GCM-SHA256': 'secure', 'DHE-RSA-AES128-SHA256': 'weak',
            'DHE-DSS-AES128-SHA256': 'weak', 'DHE-RSA-CAMELLIA128-SHA': 'weak', 'DHE-DSS-CAMELLIA128-SHA': 'weak', 'ADH-AES128-GCM-SHA256': 'insecure', 'ADH-AES128-SHA': 'insecure',
            'ADH-AES128-SHA256': 'insecure', 'ADH-AES256-GCM-SHA384': 'insecure', 'ADH-AES256-SHA': 'insecure', 'ADH-AES256-SHA256': 'insecure', 'ADH-CAMELLIA128-SHA': 'insecure',
            'ADH-CAMELLIA256-SHA': 'insecure', 'ADH-DES-CBC3-SHA': 'insecure', 'ADH-DES-CBC-SHA': 'weak', 'ADH-RC4-MD5': 'weak', 'ADH-SEED-SHA': 'insecure', 'DES-CBC-SHA': 'weak',
            'DHE-DSS-SEED-SHA': 'weak', 'DHE-RSA-SEED-SHA': 'weak', 'EDH-DSS-DES-CBC-SHA': 'weak', 'EDH-RSA-DES-CBC-SHA': 'weak', 'IDEA-CBC-SHA': 'weak', 'RC4-MD5': 'weak',
            'SEED-SHA': 'weak', 'DES-CBC3-MD5': 'weak', 'DES-CBC-MD5': 'weak', 'RC2-CBC-MD5': 'weak', 'PSK-AES256-CBC-SHA': 'weak', 'PSK-3DES-EDE-CBC-SHA': 'weak',
            'KRB5-DES-CBC3-SHA': 'weak', 'KRB5-DES-CBC3-MD5': 'weak', 'PSK-AES128-CBC-SHA': 'weak', 'PSK-RC4-SHA': 'weak', 'KRB5-RC4-SHA': 'weak', 'KRB5-RC4-MD5': 'weak',
            'KRB5-DES-CBC-SHA': 'weak', 'KRB5-DES-CBC-MD5': 'weak', 'EXP-EDH-RSA-DES-CBC-SHA': 'weak', 'EXP-EDH-DSS-DES-CBC-SHA': 'weak', 'EXP-ADH-DES-CBC-SHA': 'weak',
            'EXP-DES-CBC-SHA': 'weak', 'EXP-RC2-CBC-MD5': 'weak', 'EXP-KRB5-RC2-CBC-SHA': 'weak', 'EXP-KRB5-DES-CBC-SHA': 'weak', 'EXP-KRB5-RC2-CBC-MD5': 'weak',
            'EXP-KRB5-DES-CBC-MD5': 'weak', 'EXP-ADH-RC4-MD5': 'weak', 'EXP-RC4-MD5': 'weak', 'EXP-KRB5-RC4-SHA': 'weak', 'EXP-KRB5-RC4-MD5': 'weak'
        }
        return cipher_suites

    def _apprend_tester_result(self, item, item_type, test_name, issue_status):
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

    def get_elbv2_internet_facing(self) -> List:
        elbs = self.elbsv2
        test_name = "aws_elbv2_is_not_internet_facing"
        result = []

        for elb in elbs:
            load_balancer_arn = elb['LoadBalancerArn']
            elb_type = elb['Type']

            if elb_type == 'application' or elb_type == 'network':
                if elb['Scheme'] == 'internet-facing':
                    result.append(self._apprend_tester_result(load_balancer_arn, "aws_elbv2", test_name, "issue_found"))
                else:
                    result.append(self._apprend_tester_result(load_balancer_arn, "aws_elbv2", test_name, "no_issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_arn, "aws_elbv2", test_name, "no_issue_found"))

        return result

    def get_elb_generating_access_log(self) -> List:
        elbs = self.elbs
        test_name = "aws_elb_is_generating_access_log"
        result = []

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            response = self.aws_elbs_client.describe_load_balancer_attributes(LoadBalancerName=load_balancer_name)
            if response['LoadBalancerAttributes']['AccessLog']['Enabled']:
                # no issue
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
            else:
                # issue
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))

        return result

    def get_alb_using_secure_listener(self) -> List:
        test_name = "aws_elbv2_alb_is_using_secure_listeners"
        elbs = self.elbsv2
        result = []

        for elb in elbs:
            # check elbv2 type and only let ALB pass
            if elb['Type'] == "application":
                load_balancer_arn = elb['LoadBalancerArn']
                response = self.aws_elbsv2_client.describe_listeners(LoadBalancerArn=load_balancer_arn)
                listeners = response['Listeners']
                secure_listener_count = 0
                for listener in listeners:
                    if listener['Protocol'] == "HTTPS":
                        secure_listener_count += 1

                if secure_listener_count == len(listeners):
                    result.append(self._apprend_tester_result(load_balancer_arn, "aws_elbv2", test_name, "no_issue_found"))
                else:
                    result.append(self._apprend_tester_result(load_balancer_arn, "aws_elbv2", test_name, "issue_found"))
            else:
                continue

        return result

    def get_elbv2_generating_access_log(self) -> List:
        test_name = "aws_elbv2_is_generating_access_logs"
        result = []
        elbs = self.elbsv2

        for elb in elbs:
            elb_arn = elb['LoadBalancerArn']
            elb_type = elb['Type']

            if elb_type == 'application' or elb_type == 'network':
                elb_attributes = self.aws_elbsv2_client.describe_load_balancer_attributes(LoadBalancerArn=elb_arn)
                attributes = elb_attributes['Attributes']
                for i in attributes:
                    if i['Key'] == 'access_logs.s3.enabled':
                        if i['Value'] == 'false':
                            result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
                        else:
                            result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                        break
                    else: pass
            else:
                # access log / vpc flow logs
                arn_split = elb_arn.split(':')
                temp = arn_split[-1]
                description_temp = temp.split('loadbalancer/')
                network_interface_description = 'ELB' + ' ' + description_temp[-1]
                ec2_client = boto3.client('ec2')
                response = ec2_client.describe_network_interfaces(Filters=[{'Name': 'description', 'Values': [network_interface_description]}])
                network_interfaces = response['NetworkInterfaces']
                interface_ids = []
                for interface in network_interfaces:
                    interface_ids.append(interface['NetworkInterfaceId'])

                has_flow_logs = 0
                for id in interface_ids:
                    response = ec2_client.describe_flow_logs(Filters=[{'Name': 'resource-id', 'Values': [id]}])
                    flow_logs = response['FlowLogs']
                    if len(flow_logs) > 0:
                        has_flow_logs += 1

                if len(interface_ids) == has_flow_logs:
                    # no issue
                    result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                else:
                    # issue
                    result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
        return result

    def get_elb_listeners_using_tls(self) -> List:
        test_name = "aws_elb_listeners_using_tls_v1.2"
        result = []
        elbs = self.elbs

        for elb in elbs:
            elb_name = elb['LoadBalancerName']
            listeners = elb['ListenerDescriptions']
            secure_listeners_count = 0
            for listener in listeners:
                policy_names = listener['PolicyNames']

                if len(policy_names) > 0:
                    response = self.aws_elbs_client.describe_load_balancer_policies(PolicyNames=policy_names, LoadBalancerName=elb_name)
                    policy_descriptions = response['PolicyDescriptions']

                    found_tls_v12_count = 0
                    # look into policy attrs
                    for policy_description in policy_descriptions:
                        policy_attrs = policy_description['PolicyAttributeDescriptions']
                        for attr in policy_attrs:
                            if attr['AttributeName'] == 'Protocol-TLSv1.2' and attr['AttributeValue'] == 'true':
                                found_tls_v12_count += 1
                                break
                    if found_tls_v12_count == len(policy_descriptions):
                        secure_listeners_count += 1
                else: pass

            if secure_listeners_count == len(listeners):
                # secure
                result.append(self._apprend_tester_result(elb_name, "aws_elb", test_name, "no_issue_found"))
            else:
                # issue found
                result.append(self._apprend_tester_result(elb_name, "aws_elb", test_name, "issue_found"))
        return result

    def get_elb_listeners_securely_configured(self) -> List:
        test_name = "aws_elb_listeners_securely_configurd"
        result = []

        elbs = self.elbs

        for elb in elbs:
            listeners = elb['ListenerDescriptions']
            load_balancer_name = elb['LoadBalancerName']
            secure_listeners = 0
            for i in listeners:
                listener = i['Listener']
                if listener['InstanceProtocol'] == 'HTTPS' and listener['Protocol'] == 'HTTPS':
                    # secure
                    secure_listeners += 1
                elif listener['InstanceProtocol'] == 'SSL' and listener['Protocol'] == 'SSL':
                    # secure
                    secure_listeners += 1
                elif listener['InstanceProtocol'] == 'HTTPS' and listener['Protocol'] == 'SSL':
                    # secure
                    secure_listeners += 1
                elif listener['InstanceProtocol'] == 'SSL' and listener['Protocol'] == 'HTTPS':
                    # secure
                    secure_listeners += 1
                else: pass
            if len(listeners) == secure_listeners:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))

        return result

    def get_elb_security_policy_secure_ciphers(self) -> List:
        elbs = self.elbs
        test_name = "aws_elb_security_policy_does_not_contain_any_insecure_ciphers"
        result = []
        elb_with_issue = []
        all_elbs = []
        for elb in elbs:
            # get policies
            load_balancer_name = elb['LoadBalancerName']
            all_elbs.append(load_balancer_name)

            listeners = elb['ListenerDescriptions']
            listener_policies = []

            for listener in listeners:
                listener_policies.extend(listener['PolicyNames'])

            if len(listener_policies) > 0:
                response = self.aws_elbs_client.describe_load_balancer_policies(LoadBalancerName=load_balancer_name, PolicyNames=listener_policies)
                query_result = jmespath.search("PolicyDescriptions[].PolicyAttributeDescriptions[?AttributeValue=='true'].AttributeName", response)
                all_attrs = []

                for i in query_result:
                    all_attrs.extend(i)
                unique_set = list(set(all_attrs))
                cipher_suites = self.cipher_suites
                for i in unique_set:
                    if i.startswith('Protocol') or i.startswith('protocol'): pass
                    elif i == 'Server-Defined-Cipher-Order': pass
                    elif cipher_suites[i] == 'insecure':
                        elb_with_issue.append(load_balancer_name)
                        break
                    else: pass
            else:
                elb_with_issue.append(load_balancer_name)
        all_elbs_set = set(all_elbs)
        elb_with_issue_set = set(elb_with_issue)
        elb_with_no_issue_set = all_elbs_set.difference(elb_with_issue)

        for i in elb_with_issue_set:
            result.append(self._apprend_tester_result(i, "aws_elb", test_name, "issue_found"))

        for i in elb_with_no_issue_set:
            result.append(self._apprend_tester_result(i, "aws_elb", test_name, "no_issue_found"))

        return result

    def get_elb_has_secure_ssl_protocol(self) -> List:
        test_name = "aws_elb_has_secure_ssl_protocol"
        elbs = self.elbs
        result = []

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            ssl_policies_count = len(elb['Policies']['OtherPolicies'])
            response = self.aws_elbs_client.describe_load_balancer_policies(LoadBalancerName=load_balancer_name)
            query_result = jmespath.search("PolicyDescriptions[].PolicyAttributeDescriptions[?AttributeValue=='true'].AttributeName", response)
            ssl_with_issue = 0
            for attrs in query_result:
                for attr in attrs:
                    if attr.startswith('Protocol'): pass
                    elif attr == 'Server-Defined-Cipher-Order': pass
                    else:
                        if self.cipher_suites[attr] == 'insecure':
                            ssl_with_issue += 1
                            break
            if ssl_policies_count == ssl_with_issue:
                # insecure
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))

        return result

    def get_elbv2_using_latest_security_policy(self) -> List:
        test_name = "aws_elbv2_using_latest_security_policy"
        elbv2 = self.elbsv2
        latest_security_policies = self.latest_security_policies
        result = []
        for elb in elbv2:
            response = self.aws_elbsv2_client.describe_listeners(LoadBalancerArn=elb['LoadBalancerArn'])
            listeners = response['Listeners']
            elb_arn = elb['LoadBalancerArn']
            elb_type = elb['Type']

            if elb_type == 'application' or elb_type == 'network':
                secure_listeners = 0
                for listener in listeners:
                    ssl_policy = listener.get('SslPolicy')
                    if ssl_policy in latest_security_policies:
                        secure_listeners += 1

                if secure_listeners == len(listeners):
                    result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                else:
                    result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
            else:
                # GWLB
                result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))

        return result

    def get_elbv2_has_deletion_protection(self) -> List:
        result = []
        test_name = "aws_elbv2_has_deletion_protection_enabled"
        elbs = self.elbsv2

        for elb in elbs:
            elb_arn = elb['LoadBalancerArn']
            response = self.aws_elbsv2_client.describe_load_balancer_attributes(LoadBalancerArn=elb_arn)

            attrs = response['Attributes']

            for attr in attrs:
                if attr['Key'] == 'deletion_protection.enabled':
                    if attr['Value'] == 'true':
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                    else:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
                    break
                else: pass

        return result

    def get_elbv2_allows_https_traffic_only(self) -> List:
        result = []
        test_name = "aws_elbv2_should_allow_https_traffic_only"
        elbs = self.elbsv2

        for elb in elbs:
            elb_arn = elb['LoadBalancerArn']
            paginator = self.aws_elbsv2_client.get_paginator('describe_listeners')
            response_iterator = paginator.paginate(LoadBalancerArn=elb_arn)
            listerners = []
            for page in response_iterator:
                listerners.extend(page['Listeners'])

            for listerner in listerners:
                protocol = listerner['Protocol']
                listener_wo_https = False

                if protocol == 'HTTPS' or protocol == "TLS" or protocol == "GENEVE":
                    pass
                else:
                    listener_wo_https = True
                    break
            if listener_wo_https:
                result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
            else:
                result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))

        return result

    def get_alb_using_tls12_or_higher(self) -> List:
        result = []
        test_name = "aws_elbv2_alb_should_allow_TLSv1.2_or_higher"
        hash_map = {}
        elbs = self.elbsv2
        elb_count = len(elbs)

        if elb_count > 0:
            for elb in elbs:
                elb_arn = elb['LoadBalancerArn']
                elb_type = elb['Type']

                if elb_type == 'application':
                    paginator = self.aws_elbsv2_client.get_paginator('describe_listeners')
                    response_iterator = paginator.paginate(LoadBalancerArn=elb_arn)
                    listerners = []

                    for page in response_iterator:
                        listerners.extend(page['Listeners'])

                    for listener in listerners:
                        ssl_policy = listener['SslPolicy'] if listener.get('SslPolicy') else 'no_ssl_policy'
                        ssl_version_12 = hash_map.get(ssl_policy, None)
                        listener_with_issue = False

                        if ssl_policy != 'no_ssl_policy':
                            if ssl_version_12 is None:
                                response = self.aws_elbsv2_client.describe_ssl_policies(
                                    Names=[ssl_policy]
                                )
                                policy_details = response['SslPolicies'][0]
                                ssl_protocols = policy_details['SslProtocols']
                                ssl_versions = list(map(lambda x: float(x), list(map(lambda x: x.split('v')[-1], ssl_protocols))))
                                required_versions = list(filter(lambda x: x >= 1.2, ssl_versions))

                                if len(required_versions) == 0:
                                    hash_map[ssl_policy] = False
                                    listener_with_issue = True
                                    break
                                else: hash_map[ssl_policy] = True
                            elif ssl_version_12: listener_with_issue = False
                            else:
                                listener_with_issue = True
                                break
                        else:
                            listener_with_issue = True
                            break
                    if listener_with_issue:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
                    else:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                else: pass

        else: pass

        return result

    def get_nlb_using_tls12_or_higher(self) -> List:
        result = []
        test_name = "aws_elbv2_nlb_should_allow_TLSv1.2_or_higher"
        hash_map = {}
        elbs = self.elbsv2
        elb_count = len(elbs)

        if elb_count > 0:
            for elb in elbs:
                elb_arn = elb['LoadBalancerArn']
                elb_type = elb['Type']

                if elb_type == 'network':
                    paginator = self.aws_elbsv2_client.get_paginator('describe_listeners')
                    response_iterator = paginator.paginate(LoadBalancerArn=elb_arn)
                    listerners = []
                    for page in response_iterator:
                        listerners.extend(page['Listeners'])

                    for listener in listerners:
                        ssl_policy = listener['SslPolicy'] if listener.get('SslPolicy') else 'no_ssl_policy'
                        ssl_version_12 = hash_map.get(ssl_policy, None)
                        listener_with_issue = False

                        if ssl_policy != 'no_ssl_policy':
                            if ssl_version_12 is None:
                                response = self.aws_elbsv2_client.describe_ssl_policies(
                                    Names=[ssl_policy]
                                )
                                policy_details = response['SslPolicies'][0]
                                ssl_protocols = policy_details['SslProtocols']
                                ssl_versions = list(map(lambda x: float(x), list(map(lambda x: x.split('v')[-1], ssl_protocols))))
                                required_versions = list(filter(lambda x: x >= 1.2, ssl_versions))

                                if len(required_versions) == 0:
                                    hash_map[ssl_policy] = False
                                    listener_with_issue = True
                                    break
                                else: hash_map[ssl_policy] = True
                            elif ssl_version_12: listener_with_issue = False
                            else:
                                listener_with_issue = True
                                break
                        else:
                            listener_with_issue = True
                            break
                    if listener_with_issue:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
                    else:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                else: pass
        else: pass
        return result

    def get_elb_internet_facing(self) -> List:
        elbs = self.elbs
        test_name = "aws_elb_internet_facing"
        result = []

        if len(elbs) > 0:
            for elb in elbs:
                load_balancer_name = elb['LoadBalancerName']
                if elb['Scheme'] == 'internet-facing':
                    result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
                else:
                    result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
        else: pass
        return result

    def get_nlb_support_insecure_negotiation_policy(self) -> List:
        test_name = "aws_elbv2_nlb_should_not_support_insecure_negotiation_policy"
        result = []
        elbs = self.elbsv2
        hash_map = {}
        elb_count = len(elbs)
        if elb_count > 0:
            for elb in elbs:
                elb_arn = elb['LoadBalancerArn']
                elb_type = elb['Type']
                if elb_type == 'network':
                    paginator = self.aws_elbsv2_client.get_paginator('describe_listeners')
                    response_iterator = paginator.paginate(LoadBalancerArn=elb_arn)
                    listerners = []

                    for page in response_iterator:
                        listerners.extend(page['Listeners'])

                    for listener in listerners:
                        ssl_policy = listener['SslPolicy'] if listener.get('SslPolicy') else 'no_ssl_policy'

                        if ssl_policy != 'no_ssl_policy':
                            ssl_version_11 = hash_map.get(ssl_policy, None)
                            listener_with_issue = False

                            if ssl_version_11 is None:
                                response = self.aws_elbsv2_client.describe_ssl_policies(
                                    Names=[ssl_policy]
                                )
                                policy_details = response['SslPolicies'][0]
                                ssl_protocols = policy_details['SslProtocols']
                                ssl_versions = list(map(lambda x: float(x), list(map(lambda x: x.split('v')[-1], ssl_protocols))))

                                required_versions = list(filter(lambda x: x == 1.0 or x == 1.1, ssl_versions))

                                if len(required_versions) == 0:
                                    hash_map[ssl_policy] = False
                                else:
                                    listener_with_issue = True
                                    hash_map[ssl_policy] = True
                                    break
                            elif ssl_version_11:
                                listener_with_issue = True
                                break
                            else: listener_with_issue = False

                        else:
                            listener_with_issue = True
                            break
                    if listener_with_issue:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
                    else:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                else: pass
        else: pass

        return result

    def get_alb_certificate_should_be_renewed(self):
        test_name = "aws_elbv2_alb_ssl_certificate_should_be_renewed_30_days_in_advance"
        result = []
        elbs = self.elbsv2
        ssl_certificate_age = int(self.ssl_certificate_age) if self.ssl_certificate_age else 30

        if len(elbs) > 0:
            for elb in elbs:
                elb_type = elb['Type']
                elb_arn = elb['LoadBalancerArn']
                if elb_type == 'application':
                    paginator = self.aws_elbsv2_client.get_paginator('describe_listeners')
                    response_iterator = paginator.paginate(LoadBalancerArn=elb_arn)
                    listerners = []

                    for page in response_iterator:
                        listerners.extend(page['Listeners'])

                    elb_certificates = []

                    for listener in listerners:
                        certificates = listener.get('Certificates')
                        if certificates is not None:
                            elb_certificates.extend(certificates)
                        else:
                            elb_certificates.append(certificates)

                    elb_with_issue = False
                    for cert in elb_certificates:
                        if cert is not None:
                            cert_arn = cert['CertificateArn']
                            filtered_result = list(filter(lambda x: x == 'acm', cert_arn.split(':')))
                            if len(filtered_result) > 0:
                                response = self.aws_acm_client.describe_certificate(CertificateArn=cert_arn)
                                expire_date = datetime.date(response['Certificate']['NotAfter'])
                                current_date = datetime.date(datetime.now())
                                time_diff = (expire_date - current_date).days

                                if time_diff > ssl_certificate_age:
                                    elb_with_issue = False
                                else:
                                    elb_with_issue = True
                                    break
                            else:
                                cert_name = cert_arn.split('/')[-1]
                                response = self.aws_iam_client.get_server_certificate(ServerCertificateName=cert_name)
                                expire_date = datetime.date(response['ServerCertificate']['ServerCertificateMetadata']['Expiration'])
                                current_date = datetime.date(datetime.now())
                                time_diff = (expire_date - current_date).days

                                if time_diff > ssl_certificate_age:
                                    elb_with_issue = False
                                else:
                                    elb_with_issue = True
                                    break
                        else:
                            elb_with_issue = True
                            break

                    if elb_with_issue:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "issue_found"))
                    else:
                        result.append(self._apprend_tester_result(elb_arn, "aws_elbv2", test_name, "no_issue_found"))
                else: pass
        else: pass
        return result

    def get_elb_cross_zone_load_balancing_enabled(self):
        result = []
        test_name = "aws_elb_cross_zone_load_balancing_should_be_enabled"

        elbs = self.elbs

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            response = self.aws_elbs_client.describe_load_balancer_attributes(LoadBalancerName=load_balancer_name)
            attrs = response['LoadBalancerAttributes']

            cross_zone_enabled = attrs['CrossZoneLoadBalancing']['Enabled']
            if cross_zone_enabled:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
        return result

    def get_elb_connection_draining_enabled(self):
        result = []
        test_name = "aws_elb_connection_draining_enabled"

        elbs = self.elbs

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            response = self.aws_elbs_client.describe_load_balancer_attributes(LoadBalancerName=load_balancer_name)
            attrs = response['LoadBalancerAttributes']

            connection_draining_enabled = attrs['ConnectionDraining']['Enabled']
            if connection_draining_enabled:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))

        return result

    def get_no_registered_instances_in_an_elbv1(self):
        result = []
        test_name = "aws_elb_no_registered_instances"

        elbs = self.elbs

        for elb in elbs:
            instances = elb['Instances']
            load_balancer_name = elb['LoadBalancerName']
            if len(instances) > 0:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))

        return result

    def get_elb_should_allow_tlsv12_or_higher(self):
        result = []
        test_name = "aws_elb_should_allow_tlsv1.2_or_higher"

        elbs = self.elbs

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            response = self.aws_elbs_client.describe_load_balancer_policies(LoadBalancerName=load_balancer_name)
            query_result = jmespath.search("PolicyDescriptions[].PolicyAttributeDescriptions[?AttributeValue=='true'].AttributeName", response)

            has_issue = False

            for attrs in query_result:
                temp = list(filter(lambda x: x.startswith('Protocol'), attrs))
                filtered_result = list(map(lambda x: x.split('-')[-1], temp))
                result = list(filter(lambda x: x == 'SSLv3' or x == 'TLSv1.2', filtered_result))

                if len(result) == 0:
                    has_issue = True
                    break
                else: pass

            if has_issue:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
        return result

    def get_elb_ssl_certificate_expires_in_90_days(self):
        result = []
        test_name = "aws_elb_ssl_certificate_expires_in_90_days"
        elb_ssl_certificate_expiry = int(self.elb_ssl_certificate_expiry) if self.elb_ssl_certificate_expiry else 90
        elbs = self.elbs

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            listeners = elb.get('ListenerDescriptions')
            elb_with_issue = False

            if listeners is not None:
                for listener in listeners:
                    listener_obj = listener['Listener']
                    ssl_certificate_id = listener_obj.get('SSLCertificateId')

                    if ssl_certificate_id is not None:
                        filtered_result = list(filter(lambda x: x == "acm", ssl_certificate_id.split(":")))

                        if len(filtered_result) > 0:
                            response = self.aws_acm_client.describe_certificate(CertificateArn=ssl_certificate_id)
                            expire_date = datetime.date(response['Certificate']['NotAfter'])
                            current_date = datetime.date(datetime.now())
                            time_diff = (expire_date - current_date).days

                            if time_diff > elb_ssl_certificate_expiry:
                                elb_with_issue = False
                            else:
                                elb_with_issue = True
                                break
                        else:
                            cert_name = ssl_certificate_id.split('/')[-1]
                            response = self.aws_iam_client.get_server_certificate(ServerCertificateName=cert_name)
                            expire_date = datetime.date(response['ServerCertificate']['ServerCertificateMetadata']['Expiration'])
                            current_date = datetime.date(datetime.now())
                            time_diff = (expire_date - current_date).days

                            if time_diff > elb_ssl_certificate_expiry:
                                elb_with_issue = False
                            else:
                                elb_with_issue = True
                                break
                    else: pass

                if elb_with_issue:
                    result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
                else:
                    result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
            else: pass

        return result

    def get_elb_ssl_certificate_should_be_renewed_five_days_in_advance(self):
        result = []
        test_name = "aws_elb_ssl_certificate_should_be_renewed_five_days_before_it_expires"
        ssl_certificate_advance_renew = int(self.elb_ssl_certificate_renew) if self.elb_ssl_certificate_renew else 5
        elbs = self.elbs

        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            listeners = elb.get('ListenerDescriptions')
            elb_with_issue = False

            for listener in listeners:
                listener_obj = listener['Listener']
                ssl_certificate_id = listener_obj.get('SSLCertificateId')

                if ssl_certificate_id is not None:
                    filtered_result = list(filter(lambda x: x == "acm", ssl_certificate_id.split(":")))

                    if len(filtered_result) > 0:
                        response = self.aws_acm_client.describe_certificate(CertificateArn=ssl_certificate_id)
                        expire_date = datetime.date(response['Certificate']['NotAfter'])
                        current_date = datetime.date(datetime.now())
                        time_diff = (expire_date - current_date).days

                        if time_diff >= ssl_certificate_advance_renew:
                            elb_with_issue = False
                        else:
                            elb_with_issue = True
                            break
                    else:
                        cert_name = ssl_certificate_id.split('/')[-1]
                        response = self.aws_iam_client.get_server_certificate(ServerCertificateName=cert_name)
                        expire_date = datetime.date(response['ServerCertificate']['ServerCertificateMetadata']['Expiration'])
                        current_date = datetime.date(datetime.now())
                        time_diff = (expire_date - current_date).days

                        if time_diff >= ssl_certificate_advance_renew:
                            elb_with_issue = False
                        else:
                            elb_with_issue = True
                            break
                else: pass

            if elb_with_issue:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))

        return result

    def get_elb_supports_vulnerable_negotiation_policy(self):
        result = []
        test_name = "aws_elb_supports_vulnerable_negotiation_policy"

        elbs = self.elbs
        elb_with_issue = False
        latest_security_policies = self.latest_security_policies
        for elb in elbs:
            load_balancer_name = elb['LoadBalancerName']
            listeners = elb.get('ListenerDescriptions')
            policies = []
            for listener in listeners:
                policy_names = listener['PolicyNames']
                if len(policy_names) > 0:
                    policies.extend(policy_names)
                else:
                    policies.append(None)

            for policy in policies:
                if policy in latest_security_policies:
                    elb_with_issue = False
                else:
                    elb_with_issue = True
                    break

            if elb_with_issue:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "issue_found"))
            else:
                result.append(self._apprend_tester_result(load_balancer_name, "aws_elb", test_name, "no_issue_found"))
        return result
