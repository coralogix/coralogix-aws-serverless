import concurrent.futures
import json
import time

import boto3
import interfaces


def _format_string_to_json(text):
    return json.loads(text)


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_vpc_client = boto3.client('ec2', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.all_vpc_details = list()

    def declare_tested_service(self) -> str:
        return 'vpc'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global' or self.region_name not in self._get_regions():
            return None
        self.all_vpc_details = self._get_all_vpc()

        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_vpc_default_security_groups_in_use))
            executor_list.append(executor.submit(self.detect_vpc_security_group_per_vpc_limit))
            executor_list.append(executor.submit(self.detect_vpc_logging_status))
            executor_list.append(executor.submit(self.detect_vpc_endpoint_publicly_accessibility))
            executor_list.append(executor.submit(self.detect_network_acl_restriction_status))
            executor_list.append(executor.submit(self.detect_default_nacl_used))
            executor_list.append(executor.submit(self.detect_vpc_peering_connection))
            executor_list.append(executor.submit(self.detect_vpc_eip_in_use))
            executor_list.append(executor.submit(self.detect_vpc_dnc_resolution_enabled))

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

    def _get_all_vpc(self):
        response = self.aws_vpc_client.describe_vpcs()
        vpc_detail = []
        # If you have the required permissions, the error response is DryRunOperation .
        # Otherwise, it is UnauthorizedOperation .
        if response and 'Vpcs' in response and response['Vpcs']:
            vpc_detail.extend(response['Vpcs'])
        while 'NextToken' in response and response['NextToken']:
            response = self.aws_vpc_client.describe_vpcs(NextToken=response['NextToken'])
            if response and 'Vpcs' in response and response['Vpcs']:
                vpc_detail.extend(response['Vpcs'])
        return vpc_detail

    def _append_vpc_test_result(self, vpc_detail, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": vpc_detail['VpcId'],
            "item_type": "vpc",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _append_epi_test_result(self, eip_detail, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": eip_detail['AllocationId'],
            "item_type": "vpc_elastic_ip",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def _check_logging_status(self, test_name, ):
        logging_result = []
        for vpc_detail in self.all_vpc_details:
            result = self.aws_vpc_client.describe_flow_logs(Filters=[
                {
                    'Name': 'resource-id',
                    'Values': [vpc_detail['VpcId']]
                },
            ])
            if result and result['FlowLogs']:
                logging_result.append(self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
            else:
                logging_result.append(self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))
        return logging_result

    def _check_vpc_public_accessibility(self, test_name):
        vpc_public_accessible = []
        for vpc_detail in self.all_vpc_details:
            result = self.aws_vpc_client.describe_vpc_endpoints(Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_detail['VpcId']]
                },
            ])
            if result and 'VpcEndpoints' in result and result['VpcEndpoints']:
                for vpc_end_point_data in result['VpcEndpoints']:
                    if 'PolicyDocument' in vpc_end_point_data and vpc_end_point_data['PolicyDocument']:
                        policy_document_json_data = _format_string_to_json(vpc_end_point_data['PolicyDocument'])
                        if 'Statement' in policy_document_json_data:
                            issue_found = False
                            for statement_dict in policy_document_json_data['Statement']:
                                if 'Principal' in statement_dict and statement_dict[
                                    'Principal'] == '*' or 'Principal' in statement_dict and 'AWS' in statement_dict[
                                    'Principal'] and statement_dict['Principal']['AWS'] == '*':
                                    issue_found = True
                                    break
                            if issue_found:
                                vpc_public_accessible.append(
                                    self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))
                            else:
                                vpc_public_accessible.append(
                                    self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
            else:
                vpc_public_accessible.append(
                    self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
        return vpc_public_accessible

    def _check_ingress_administration_ports_range_for_network_acls_inbound_rule(self, test_name):
        ingress_traffic_test_result = []
        for vpc_detail in self.all_vpc_details:
            vpc_id = vpc_detail['VpcId']
            response = self.aws_vpc_client.describe_network_acls(Filters=[{
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }, ])
            if response and 'NetworkAcls' in response and len(response['NetworkAcls']):
                for acl in response['NetworkAcls']:
                    issue_found = False
                    for network_acl_rules in acl['Entries']:
                        if 'Egress' in network_acl_rules and not network_acl_rules['Egress'] and network_acl_rules[
                            'RuleAction'].lower() == 'allow':
                            if 'PortRange' not in network_acl_rules:
                                issue_found = True
                                break
                            # elif 'PortRange' in network_acl_rules and network_acl_rules['PortRange'] == []:
                    if issue_found:
                        ingress_traffic_test_result.append(
                            self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))
                    else:
                        ingress_traffic_test_result.append(
                            self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
            else:
                ingress_traffic_test_result.append(
                    self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
        return ingress_traffic_test_result

    def _check_default_nacl_used(self, test_name):
        default_nacl_used_result = []
        for vpc_detail in self.all_vpc_details:
            network_acls_response = self.aws_vpc_client.describe_network_acls(Filters=[{
                'Name': 'vpc-id',
                'Values': [vpc_detail['VpcId']]
            }])
            issue_found = False
            if 'NetworkAcls' in network_acls_response and network_acls_response['NetworkAcls']:
                for network_acls_dict in network_acls_response['NetworkAcls']:
                    if 'IsDefault' in network_acls_dict and network_acls_dict['IsDefault']:
                        issue_found = True
                        break
            else:
                issue_found = True

            if issue_found:
                default_nacl_used_result.append(self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))
            else:
                default_nacl_used_result.append(self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))

        return default_nacl_used_result

    def _check_vpc_dns_resolution_enabled(self, test_name):
        vpc_dns_resolution_result = []
        for vpc_detail in self.all_vpc_details:
            dns_support_response = self.aws_vpc_client.describe_vpc_attribute(
                Attribute='enableDnsSupport',
                VpcId=vpc_detail['VpcId']
            )
            if 'EnableDnsSupport' in dns_support_response and dns_support_response['EnableDnsSupport'] and 'Value' in \
                    dns_support_response['EnableDnsSupport'] and dns_support_response['EnableDnsSupport']['Value']:
                vpc_dns_resolution_result.append(self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
            else:
                vpc_dns_resolution_result.append(self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))

        return vpc_dns_resolution_result

    def detect_vpc_default_security_groups_in_use(self):
        result = []
        test_name = 'aws_vpc_default_security_groups_in_use'
        all_ec2_instance = []
        ec2_response = self.aws_vpc_client.describe_instances()
        if ec2_response and 'Reservations' in ec2_response and ec2_response['Reservations']:
            for reservations_dict in ec2_response['Reservations']:
                if 'Instances' in reservations_dict and reservations_dict['Instances']:
                    all_ec2_instance.extend(reservations_dict['Instances'])
        for ec2_instance_dict in all_ec2_instance:
            response = self.aws_vpc_client.describe_security_groups(
                Filters=[
                    {
                        'Name': 'group-id',
                        'Values': [security_group_dict['GroupId'] for security_group_dict in
                                   ec2_instance_dict['SecurityGroups']]
                    }
                ])
            if 'SecurityGroups' in response and response['SecurityGroups']:
                for security_groups_dict in response['SecurityGroups']:
                    if 'GroupName' in security_groups_dict and security_groups_dict['GroupName'] == 'default':
                        ec2_instance_dict['VpcId'] = security_groups_dict['VpcId'] + '@@' + security_groups_dict[
                            'GroupId']
                        result.append(self._append_vpc_test_result(ec2_instance_dict, test_name, 'issue_found'))
                        ec2_instance_dict['VpcId'] = security_groups_dict['VpcId']
                    else:
                        result.append(self._append_vpc_test_result(ec2_instance_dict, test_name, 'no_issue_found'))
        return result

    def detect_vpc_security_group_per_vpc_limit(self):
        result = []
        test_name = 'aws_vpc_security_group_per_vpc_limit'
        for vpc_detail in self.all_vpc_details:
            security_groups_response = self.aws_vpc_client.describe_security_groups(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_detail['VpcId']]}], MaxResults=451)
            count = len(security_groups_response['SecurityGroups'])
            if count >= 450:
                result.append(self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))
            else:
                result.append(self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
        return result

    def detect_vpc_logging_status(self) -> list:
        return self._check_logging_status('aws_vpc_flow_logging_is_enabled_in_all_vpcs')

    def detect_vpc_endpoint_publicly_accessibility(self):
        return self._check_vpc_public_accessibility('aws_vpc_endpoint_publicly_accessible')

    def detect_network_acl_restriction_status(self):
        return self._check_ingress_administration_ports_range_for_network_acls_inbound_rule(
            'aws_vpc_network_acl_do_not_allow_ingress_from_0.0.0.0_to_remote_server_administration_ports')

    def detect_default_nacl_used(self):
        return self._check_default_nacl_used('aws_vpc_default_nacl_used')

    def detect_vpc_peering_connection(self):
        vpc_peering_connection_status = []
        test_name = 'aws_vpc_unauthorized_vpc_peering'
        for vpc_detail in self.all_vpc_details:
            issue_found = []
            vpc_peering_connection_response = self.aws_vpc_client.describe_vpc_peering_connections(Filters=[
                {
                    'Name': 'requester-vpc-info.vpc-id',
                    'Values': [vpc_detail['VpcId']]
                }
            ])
            if vpc_peering_connection_response and 'VpcPeeringConnections' in vpc_peering_connection_response and \
                    vpc_peering_connection_response['VpcPeeringConnections']:
                for vpc_peering_connection_dict in vpc_peering_connection_response['VpcPeeringConnections']:
                    if vpc_peering_connection_dict['AccepterVpcInfo']['OwnerId'] != \
                            vpc_peering_connection_dict['RequesterVpcInfo']['OwnerId']:
                        issue_found.append(vpc_peering_connection_dict['VpcPeeringConnectionId'])

            if issue_found:
                vpc_id = vpc_detail['VpcId']
                for data in issue_found:
                    vpc_detail['VpcId'] = vpc_id + '@@' + data
                    vpc_peering_connection_status.append(
                        self._append_vpc_test_result(vpc_detail, test_name, 'issue_found'))
            else:
                vpc_peering_connection_status.append(
                    self._append_vpc_test_result(vpc_detail, test_name, 'no_issue_found'))
        return vpc_peering_connection_status

    def detect_vpc_eip_in_use(self):
        result = []
        test_name = 'aws_vpc_ip_address_is_attached_to_a_host_or_eni'
        response = self.aws_vpc_client.describe_addresses()
        for address_dict in response['Addresses']:
            if 'AssociationId' not in address_dict or (
                    'AssociationId' in address_dict and not address_dict['AssociationId']):
                result.append(self._append_epi_test_result(address_dict, test_name, 'issue_found'))
            else:
                result.append(self._append_epi_test_result(address_dict, test_name, 'no_issue_found'))
        return result

    def detect_vpc_dnc_resolution_enabled(self):
        return self._check_vpc_dns_resolution_enabled('aws_vpc_dnc_resolution_enabled')

