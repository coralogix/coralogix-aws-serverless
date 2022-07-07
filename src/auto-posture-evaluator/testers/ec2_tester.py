import os
import time
from typing import Dict, List, Set
import boto3
import interfaces
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name: str) -> None:
        self.aws_region = region_name
        self.all_aws_regions = self._get_all_aws_regions()
        self.aws_ec2_client = boto3.client('ec2', region_name=region_name)
        self.aws_ec2_resource = boto3.resource('ec2', region_name=region_name)
        self.aws_nfw_client = boto3.client('network-firewall', region_name=region_name)
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.security_groups = []
        self.set_security_group = []
        self.ec2_instances = []
        self.sensitive_instance_tag = os.environ.get('AUTOPOSTURE_EC2_SENSITIVE_TAG')
        self.per_region_max_cpu_count_diff = os.environ.get('AUTOPOSTURE_PER_REGION_MAX_CPU_COUNT_DIFF')

    def declare_tested_service(self) -> str:
        return 'ec2'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        all_aws_regions = self._get_all_aws_regions()

        if any([self.aws_region == region for region in all_aws_regions]):
            self.security_groups = self.aws_ec2_resource.security_groups.all()
            self.set_security_group = self._get_all_security_group_ids(self.security_groups)
            all_inbound_permissions = self._get_all_inbound_permissions_by_security_groups(self.security_groups)
            all_outbound_permissions = self._get_all_outbound_permissions_by_security_groups(self.security_groups)
            self.ec2_instances = self._get_all_ec2_instances(self.aws_ec2_client)
            region_names = self._get_ec2_region_names()

            executor_list = []
            return_values = []
            with ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.get_inbound_http_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_https_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_mongodb_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_mysql_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_mssql_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_ssh_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_rdp_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_dns_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_telnet_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_rpc_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_icmp_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_security_group_allows_ingress_from_anywhere, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_vpc_default_security_group_restrict_traffic))
                executor_list.append(executor.submit(self.get_outbound_access_to_all_ports, all_outbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_oracle_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_ftp_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_smtp_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_elasticsearch_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_tcp_netbios_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_udp_netbios, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_inbound_cifs_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_instance_uses_metadata_service_version_2, self.ec2_instances))
                executor_list.append(executor.submit(self.get_security_group_allows_https_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_security_group_allows_inbound_access_from_ports_higher_than_1024, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_unrestricted_admin_port_access_in_network_acl))
                executor_list.append(executor.submit(self.get_internet_gateway_presence_detected, self.ec2_instances))
                executor_list.append(executor.submit(self.get_sensitive_instance_tenancy_not_dedicated, self.ec2_instances))
                executor_list.append(executor.submit(self.get_aws_config_not_enabled_for_all_regions, region_names))
                executor_list.append(executor.submit(self.get_nearing_regional_limit_for_elastic_ip_addresses, region_names))
                executor_list.append(executor.submit(self.get_ec2_instance_iam_role_not_enabled, self.ec2_instances))
                executor_list.append(executor.submit(self.get_security_group_allows_inbound_traffic, all_inbound_permissions))
                executor_list.append(executor.submit(self.get_instance_with_upcoming_system_maintenance_scheduled_event, self.ec2_instances))
                executor_list.append(executor.submit(self.get_instance_with_upcoming_instance_stop_scheduled_event, self.ec2_instances))
                executor_list.append(executor.submit(self.get_instance_with_upcoming_instance_reboot_scheduled_event, self.ec2_instances))
                executor_list.append(executor.submit(self.get_instance_with_upcoming_system_reboot_scheduled_event, self.ec2_instances))
                executor_list.append(executor.submit(self.get_region_nearing_limits_of_ec2_instances, region_names))
                executor_list.append(executor.submit(self.get_elastic_ip_in_use))
                executor_list.append(executor.submit(self.get_unrestricted_mysql_access, all_inbound_permissions))
                executor_list.append(executor.submit(self.detect_classic_ec2_instances))
                executor_list.append(executor.submit(self.get_security_group_should_allow_access_to_specific_private_networks_only))
                executor_list.append(executor.submit(self.get_network_firewall_used))

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

    def _get_result_object(self, item, item_type, test_name, issue_status):
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

    def _get_all_security_group_ids(self, instances) -> Set:
        return set(list(map(lambda i: i.id, list(instances))))

    def _get_all_inbound_permissions(self, instances):
        all_inbound_permissions = []
        for instance in instances:
            security_groups = instance.security_groups
            for security_group in security_groups:
                inbound_permissions = self.aws_ec2_resource.SecurityGroup(security_group['GroupId']).ip_permissions
                for i in inbound_permissions:
                    i['instance'] = instance
                    i['security_group'] = security_group
                    all_inbound_permissions.append(i)
        return all_inbound_permissions

    def _get_all_inbound_permissions_by_security_groups(self, security_groups) -> List[Dict]:
        inbound_rules = []
        for security_group in security_groups:
            rules = security_group.ip_permissions
            for rule in rules:
                rule['security_group'] = security_group
                inbound_rules.append(rule)
        return inbound_rules

    def _get_all_outbound_permissions_by_security_groups(self, security_groups) -> List[Dict]:
        outbound_rules = []
        for security_group in security_groups:
            rules = security_group.ip_permissions_egress
            for rule in rules:
                rule['security_group'] = security_group
                outbound_rules.append(rule)
        return outbound_rules

    def _get_inbound_port_access(self, all_inbound_permissions, target_port, test_name, protocol="tcp") -> List[Dict]:
        result = []
        instances = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == "-1") or ((permission['FromPort']
                         <= target_port and permission['ToPort'] >= target_port) and permission['IpProtocol'] == protocol), all_inbound_permissions))))
        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))
        return result

    def _get_ec2_region_names(self) -> List:
        regions = self.aws_ec2_client.describe_regions()
        region_names = []
        for region in regions['Regions']:
            region_names.append(region['RegionName'])
        return region_names

    def _get_all_ec2_instances(self, client, filters=[]) -> List:
        instances = []
        can_paginate = client.can_paginate('describe_instances')
        if can_paginate:
            reservations = []
            paginator = client.get_paginator('describe_instances')
            response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50}, Filters=filters)
            for page in response_iterator:
                reservations.extend(page['Reservations'])
            for reservation in reservations:
                instances.extend(reservation['Instances'])
        else:
            response = client.describe_instances(Filters=filters)
            for reservation in response['Reservations']:
                instances.extend(reservation['Instances'])
        return instances

    def _get_service_clients_for_all_regions(self, client_name):
        regions = self._get_ec2_region_names()
        clients = []
        for region in regions:
            clients.append(boto3.client(client_name, region_name=region))
        return clients

    def get_inbound_http_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_http_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 80, test_name)

    def get_inbound_https_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_https_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 443, test_name)

    def get_inbound_mongodb_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_mongodb_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 27017, test_name)

    def get_inbound_mysql_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_mysql_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 3306, test_name)

    def get_inbound_mssql_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_mssql_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 1433, test_name)

    def get_inbound_ssh_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_ssh_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 22, test_name)

    def get_inbound_rdp_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_rdp_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 3389, test_name)

    def get_inbound_postgresql_access(self, all_inbound_permissions) -> List:
        test_name = "aws_ec2_inbound_postgresql_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 5432, test_name)

    def get_inbound_tcp_netbios_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_tcp_netbios_access_restricted"
        result = []
        instances = []
        NAMERESPORT = 137
        SESSIONPORT = 139
        DATAGRAMPORT = 138

        instancse_137 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= NAMERESPORT and permission['ToPort'] >= NAMERESPORT) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instancse_137)
        instancse_139 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= SESSIONPORT and permission['ToPort'] >= SESSIONPORT) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instancse_139)
        instances_138 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1') or ((permission['FromPort']
                             <= DATAGRAMPORT and permission['ToPort'] >= DATAGRAMPORT) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_138)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_inbound_dns_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_dns_access_restricted"
        result = []
        target_port = 53
        instances = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == "-1") or ((permission['FromPort']
                         <= target_port and permission['ToPort'] >= target_port) and (permission['IpProtocol'] == "tcp" or permission['IpProtocol'] == "udp")), all_inbound_permissions))))
        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))
        return result

    def get_inbound_telnet_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_telnet_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 23, test_name)

    def get_inbound_cifs_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_cifs_access_restricted"
        result = []
        instances = []
        PORT137 = 137
        PORT138 = 138
        PORT139 = 139
        PORT445 = 445
        PORT3020 = 3020

        instancse_137 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= PORT137 and permission['ToPort'] >= PORT137) and permission['IpProtocol'] == 'udp'), all_inbound_permissions))))
        instances.extend(instancse_137)
        instancse_138 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= PORT138 and permission['ToPort'] >= PORT138) and permission['IpProtocol'] == 'udp'), all_inbound_permissions))))
        instances.extend(instancse_138)
        instancse_139 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= PORT139 and permission['ToPort'] >= PORT139) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instancse_139)
        instancse_445 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= PORT445 and permission['ToPort'] >= PORT445) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instancse_445)
        instancse_3020 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                              or ((permission['FromPort'] <= PORT3020 and permission['ToPort'] >= PORT3020) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instancse_3020)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_inbound_elasticsearch_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_elasticsearch_access_restricted"
        results = []
        instances = []
        PORT9200 = 9200
        PORT9300 = 9300
        instances_9200 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                              or ((permission['FromPort'] <= PORT9200 and permission['ToPort'] >= PORT9200) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_9200)
        instances_9300 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                              or ((permission['FromPort'] <= PORT9300 and permission['ToPort'] >= PORT9300) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_9300)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            results.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            results.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return results

    def get_inbound_smtp_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_smtp_access_restricted"
        result = []
        PORT25 = 25
        PORT587 = 587
        instances = []
        instances_25 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                            or ((permission['FromPort'] <= PORT25 and permission['ToPort'] >= PORT25) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_25)
        instances_587 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= PORT587 and permission['ToPort'] >= PORT587) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_587)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_inbound_rpc_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_rpc_access_restricted"
        return self._get_inbound_port_access(all_inbound_permissions, 135, test_name)

    def get_inbound_ftp_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_ftp_access_restricted"
        result = []
        instances = []
        DATAPORT = 20
        COMMANDPORT = 21
        instances_20 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                            or ((permission['FromPort'] <= DATAPORT and permission['ToPort'] >= DATAPORT) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_20)
        instances_21 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                            or ((permission['FromPort'] <= COMMANDPORT and permission['ToPort'] >= COMMANDPORT) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_21)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_inbound_udp_netbios(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_udp_netbios_access_restricted"
        result = []
        instances = []
        NAMERESPORT = 137
        DATAGRAMPORT = 138
        SESSIONPORT = 139

        instancse_137 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                             or ((permission['FromPort'] <= NAMERESPORT and permission['ToPort'] >= NAMERESPORT) and permission['IpProtocol'] == 'udp'), all_inbound_permissions))))
        instances.extend(instancse_137)
        instancse_138 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1') or ((permission['FromPort']
                             <= DATAGRAMPORT and permission['ToPort'] >= DATAGRAMPORT) and permission['IpProtocol'] == 'udp'), all_inbound_permissions))))
        instances.extend(instancse_138)
        instance_139 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                            or ((permission['FromPort'] <= SESSIONPORT and permission['ToPort'] >= SESSIONPORT) and permission['IpProtocol'] == 'udp'), all_inbound_permissions))))
        instances.extend(instance_139)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_outbound_access_to_all_ports(self, all_outbound_permissions):
        test_name = "aws_ec2_outbound_access_to_all_ports_restricted"
        result = []
        security_groups = []

        for outbound_permission in all_outbound_permissions:
            if outbound_permission['IpProtocol'] == '-1':
                security_groups.append(outbound_permission['security_group'].id)

        security_groups_with_issues = set(security_groups)
        security_groups_with_no_issues = self.set_security_group.difference(security_groups_with_issues)
        for i in security_groups_with_issues:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in security_groups_with_no_issues:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_vpc_default_security_group_restrict_traffic(self):
        test_name = "aws_ec2_vpc_default_security_group_restrict_all_traffic"
        result = []
        vpcs = self._get_all_vpcs()
        all_vpcs = []
        for vpc in vpcs:
            all_vpcs.append(vpc['VpcId'])
        all_vpcs = set(all_vpcs)

        vpcs_with_issue = []
        security_groups = self.security_groups
        for security_group in security_groups:
            if security_group.group_name == "default":
                ingress_rules = security_group.ip_permissions
                egress_rules = security_group.ip_permissions_egress
                ingress_results = list(filter(lambda rule: (rule['IpProtocol'] == "-1") or (rule['FromPort'] >= 0 and rule['ToPort'] <= 65535), ingress_rules))
                egress_results = list(filter(lambda rule: (rule['IpProtocol'] == "-1") or (rule['FromPort'] >= 0 and rule['ToPort'] <= 65535), egress_rules))

                if len(ingress_results) != 0 or len(egress_results) != 0:
                    vpcs_with_issue.append(security_group.vpc_id)

        vpcs_with_issue = set(vpcs_with_issue)
        vpcs_with_no_issue = all_vpcs.difference(vpcs_with_issue)

        for vpc in vpcs_with_issue:
            result.append(self._get_result_object(vpc, "aws_vpc", test_name, "issue_found"))

        for vpc in vpcs_with_no_issue:
            result.append(self._get_result_object(vpc, "aws_vpc", test_name, "no_issue_found"))
        return result

    def get_inbound_oracle_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_oracle_access_restricted"
        PORT1521 = 1521
        PORT2483 = 2483
        PORT2484 = 2484

        result = []
        instances = []

        instances_1521 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1') or (permission['FromPort']
                              <= PORT1521 and permission['ToPort'] >= PORT1521 and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))))
        instances.extend(instances_1521)
        instances_2483 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                              or (permission['FromPort'] <= PORT2483 and permission['ToPort'] >= PORT2483), all_inbound_permissions))))
        instances.extend(instances_2483)
        instances_2484 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                              or (permission['FromPort'] <= PORT2484 and permission['ToPort'] >= PORT2484), all_inbound_permissions))))
        instances.extend(instances_2484)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_inbound_icmp_access(self, all_inbound_permissions):
        test_name = "aws_ec2_inbound_icmp_access_restricted"
        result = []
        instances = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: permission['IpProtocol']
                         == "icmp" or permission['IpProtocol'] == "-1" or permission['IpProtocol'] == "icmpv6", all_inbound_permissions))))
        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))
        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def get_security_group_allows_ingress_from_anywhere(self, all_inbound_permissions):
        test_name = "aws_ec2_security_group_allows_ingress_to_remote_administration_ports_from_anywhere"
        result = []
        security_groups = []
        SSHPORT = 22
        RDPPORT = 3389
        for i in all_inbound_permissions:
            if i['IpProtocol'] == "-1" and len(i['IpRanges']) == 0: pass
            elif i['IpProtocol'] == "-1" and len(i['IpRanges']) != 0:
                if any([ip['CidrIp'] == '0.0.0.0/0' for ip in i['IpRanges']]):
                    security_groups.append(i['security_group'].id)
                if any([ip['CidrIpv6'] == '::/0' for ip in i['Ipv6Ranges']]):
                    security_groups.append(i['security_group'].id)

            elif (i['FromPort'] <= SSHPORT and i['ToPort'] >= SSHPORT) or (i['FromPort'] <= RDPPORT and i['ToPort'] >= RDPPORT):
                if any([ip['CidrIp'] == '0.0.0.0/0' for ip in i['IpRanges']]):
                    security_groups.append(i['security_group'].id)
                if any([ip['CidrIpv6'] == '::/0' for ip in i['Ipv6Ranges']]):
                    security_groups.append(i['security_group'].id)
            else:
                continue
        security_groups_with_issue = set(security_groups)
        security_groups_with_no_issue = self.set_security_group.difference(security_groups_with_issue)

        for s in security_groups_with_issue:
            result.append(self._get_result_object(s, "ec2_security_group", test_name, "issue_found"))

        for s in security_groups_with_no_issue:
            result.append(self._get_result_object(s, "ec2_security_group", test_name, "no_issue_found"))
        return result

    def get_instance_uses_metadata_service_version_2(self, instances):
        test_name = "aws_ec2_instance_uses_metadata_service_version_2"
        result = []

        for instance in instances:
            instance_id = instance['InstanceId']
            if instance['MetadataOptions']['HttpTokens'] == 'optional':
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "issue_found"))
            else:
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "no_issue_found"))

        return result

    def get_security_group_allows_https_access(self, all_inbound_permissions):
        test_name = "aws_ec2_security_group_allows_https_access"
        results = []
        instances = []
        PORT443 = 443

        instances_443 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1') or ((permission['FromPort'] <= PORT443 and permission['ToPort'] >= PORT443)
                             and permission['IpProtocol'] == 'tcp' and any([range.get('CidrIp', '') == '0.0.0.0/0' or range.get('CidrIp', '') == '::/0' for range in permission['IpRanges']])), all_inbound_permissions))))
        instances.extend(instances_443)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            results.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            results.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return results

    def get_security_group_allows_inbound_access_from_ports_higher_than_1024(self, all_inbound_permissions):
        test_name = "aws_ec2_security_group_allows_inbound_access_from_ports_higher_than_1024"
        results = []
        instances = []
        PORT1024 = 1024
        HISHESTPORT = 65535
        instances_1024 = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: (permission['IpProtocol'] == '-1')
                                                                                or ((permission['FromPort'] >= PORT1024 and permission['ToPort'] <= HISHESTPORT)
                                                                                    and (any([range.get('CidrIp', '') == '0.0.0.0/0' or range.get('CidrIp', '') == '::/0' for range in permission['IpRanges']])
                                                                                         or any([range.get('CidrIpv6', '') == '::/0' for range in permission['Ipv6Ranges']]))), all_inbound_permissions))))

        instances.extend(instances_1024)

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            results.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            results.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))

        return results

    def get_unrestricted_admin_port_access_in_network_acl(self):
        test_name = "aws_ec2_unrestricted_admin_port_access_in_network_acl"
        results = []
        can_paginate = self.aws_ec2_client.can_paginate('describe_network_acls')
        acls = []
        filters = [{'Name': 'entry.protocol', 'Values': ['6']}]
        if can_paginate:
            paginator = self.aws_ec2_client.get_paginator('describe_network_acls')
            response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50}, Filters=filters)
            for page in response_iterator:
                acls.extend(page['NetworkAcls'])
        else:
            response = self.aws_ec2_client.describe_network_acls(Filters=filters)
            acls.extend(response)

        for acl in acls:
            issue_found = False
            for entry in acl['Entries']:
                if entry.get('CidrBlock') == '0.0.0.0/0' and entry.get('RuleAction') == 'allow' and (entry.get('PortRange')['to'] == 3389 or entry.get('PortRange')['from'] == 3389 or entry.get('PortRange')['to'] == 22 or entry.get('PortRange')['from'] == 22):
                    issue_found = True
                    break
            if issue_found:
                results.append(self._get_result_object(acl['NetworkAclId'], "ec2_network_acl", test_name, "issue_found"))
            else:
                results.append(self._get_result_object(acl['NetworkAclId'], "ec2_network_acl", test_name, "no_issue_found"))
        return results

    def get_internet_gateway_presence_detected(self, instances):
        test_name = "aws_ec2_internet_gateway_presence_detected"
        result = []
        gateways = []
        can_paginate = self.aws_ec2_client.can_paginate('describe_internet_gateways')
        if can_paginate:
            paginator = self.aws_ec2_client.get_paginator('describe_internet_gateways')
            response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50})
            for response in response_iterator:
                gateways.extend(response['InternetGateways'])
        else:
            response = self.aws_ec2_client.describe_internet_gateways()
            for response in response['InternetGateways']:
                gateways.extend(response)
        vpc_ids = []
        for gateway in gateways:
            for attachment in gateway['Attachments']:
                vpc_ids.append(attachment['VpcId'])

        for instance in instances:
            instance_id = instance['InstanceId']
            vpc_id = instance.get('VpcId')
            if vpc_id and vpc_id in vpc_ids:
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "issue_found"))
            else:
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "no_issue_found"))

        return result

    def get_sensitive_instance_tenancy_not_dedicated(self, instances):
        test_name = "aws_ec2_sensitive_instance_tenancy_not_dedicated"
        result = []
        sensitive_tag = self.sensitive_instance_tag if self.sensitive_instance_tag else "sensitive"
        for instance in instances:
            instance_tags = instance.get('Tags')
            instance_id = instance['InstanceId']
            if instance_tags is not None:
                if any([tag['Value'] == sensitive_tag for tag in instance_tags]) and \
                        instance['Placement']['Tenancy'] != 'dedicated':
                    result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "issue_found"))
                else:
                    result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "no_issue_found"))
            else: pass
        return result

    def get_aws_config_not_enabled_for_all_regions(self, region_names):
        test_name = "aws_ec2_aws_config_not_enabled_for_all_regions"
        clients = self._get_service_clients_for_all_regions('config')
        result = []
        for i in range(len(clients)):
            response = clients[i].describe_configuration_recorder_status()
            configuration_records_status = response.get('ConfigurationRecordersStatus')
            if configuration_records_status is not None:
                if len(configuration_records_status) == 0 or configuration_records_status[0]['recording'] is False:
                    result.append(self._get_result_object(region_names[i], "ec2_region", test_name, "issue_found"))
                else:
                    result.append(self._get_result_object(region_names[i], "ec2_region", test_name, "no_issue_found"))
            else: pass

        return result

    def get_nearing_regional_limit_for_elastic_ip_addresses(self, region_names):
        test_name = "aws_ec2_nearing_regional_limit_for_elastic_ip_addresses"
        clients = self._get_service_clients_for_all_regions('ec2')
        result = []
        for i in range(len(clients)):
            response = clients[i].describe_account_attributes(AttributeNames=['vpc-max-elastic-ips'])
            account_attrs = response['AccountAttributes']
            if account_attrs:
                limit = response['AccountAttributes'][0]['AttributeValues'][0]['AttributeValue']
                addresses = clients[i].describe_addresses(Filters=[{'Name': 'domain', 'Values': ['vpc']}])
                if len(addresses['Addresses']) == limit:
                    result.append(self._get_result_object(region_names[i], "ec2_region", test_name, "issue_found"))
                else:
                    result.append(self._get_result_object(region_names[i], "ec2_region", test_name, "no_issue_found"))
            else: pass
        return result

    def get_ec2_instance_iam_role_not_enabled(self, instances):
        test_name = "aws_ec2_instance_iam_role_not_enabled"
        result = []
        for instance in instances:
            instance_id = instance['InstanceId']
            iam_instance_profile = instance.get('IamInstanceProfile')
            if not iam_instance_profile or not iam_instance_profile.get('Id') or not iam_instance_profile.get('Arn'):
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "issue_found"))
            else:
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "no_issue_found"))
        return result

    def _get_all_vpcs(self):
        vpcs = []
        paginator = self.aws_ec2_client.get_paginator('describe_vpcs')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            vpcs.extend(page['Vpcs'])

        return vpcs

    def get_security_group_allows_inbound_traffic(self, all_inbound_permissions):
        test_name = "aws_ec2_security_group_allows_all_inbound_traffic"
        result = []
        instances = list(map(lambda i: i['security_group'].id, list(filter(lambda permission: any([range.get('CidrIp', '')
                         == '0.0.0.0/0' or range.get('CidrIp', '') == '::/0' for range in permission['IpRanges']]), all_inbound_permissions))))

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))
        return result

    def get_instance_with_upcoming_system_maintenance_scheduled_event(self, instances):
        test_name = "aws_ec2_instance_with_upcoming_system_maintenance_scheduled_event"
        result = []
        instances_with_issue = self.aws_ec2_client.describe_instance_status(Filters=[{'Name': 'event.code', 'Values': ['system-maintenance']}])
        instances_with_issue = set(list(map(lambda x: x['InstanceId'], instances_with_issue['InstanceStatuses'])))
        instances_with_no_issue = set(list(map(lambda x: x['InstanceId'], instances))).difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "no_issue_found"))
        return result

    def get_instance_with_upcoming_instance_stop_scheduled_event(self, instances):
        test_name = "aws_ec2_instance_with_upcoming_instance_stop_scheduled_event"
        result = []
        instances_with_issue = self.aws_ec2_client.describe_instance_status(Filters=[{'Name': 'event.code', 'Values': ['instance-stop']}])
        instances_with_issue = set(list(map(lambda x: x['InstanceId'], instances_with_issue['InstanceStatuses'])))
        instances_with_no_issue = set(list(map(lambda x: x['InstanceId'], instances))).difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "no_issue_found"))
        return result

    def get_instance_with_upcoming_instance_reboot_scheduled_event(self, instances):
        test_name = "aws_ec2_instance_with_upcoming_instance_reboot_scheduled_event"
        result = []
        instances_with_issue = self.aws_ec2_client.describe_instance_status(Filters=[{'Name': 'event.code', 'Values': ['instance-reboot']}])
        instances_with_issue = set(list(map(lambda x: x['InstanceId'], instances_with_issue['InstanceStatuses'])))
        instances_with_no_issue = set(list(map(lambda x: x['InstanceId'], instances))).difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "no_issue_found"))
        return result

    def get_instance_with_upcoming_system_reboot_scheduled_event(self, instances):
        test_name = "aws_ec2_instance_with_upcoming_system_reboot_scheduled_event"
        result = []
        instances_with_issue = self.aws_ec2_client.describe_instance_status(Filters=[{'Name': 'event.code', 'Values': ['system-reboot']}])
        instances_with_issue = set(list(map(lambda x: x['InstanceId'], instances_with_issue['InstanceStatuses'])))
        instances_with_no_issue = set(list(map(lambda x: x['InstanceId'], instances))).difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "issue_found"))

        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_instance", test_name, "no_issue_found"))
        return result

    def get_region_nearing_limits_of_ec2_instances(self, region_names):
        test_name = "aws_ec2_region_nearing_limits_of_ec2_instances"
        result = []
        cpu_count_limit = int(self.per_region_max_cpu_count_diff) if self.per_region_max_cpu_count_diff else 50
        service_quota_clients = self._get_service_clients_for_all_regions('service-quotas')
        ec2_clients = self._get_service_clients_for_all_regions('ec2')
        for i in range(len(region_names)):
            region_vcpu_quota = service_quota_clients[i].get_service_quota(ServiceCode='ec2', QuotaCode='L-1216C47A')
            region_limit = region_vcpu_quota['Quota']['Value']
            instances = self._get_all_ec2_instances(ec2_clients[i], filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
            current_cpu_count = 0
            for instance in instances:
                current_cpu_count += instance['CpuOptions']['CoreCount'] * instance['CpuOptions']['ThreadsPerCore']
            if region_limit - current_cpu_count <= cpu_count_limit:
                result.append(self._get_result_object(region_names[i], "ec2_region", test_name, "issue_found"))
            else:
                result.append(self._get_result_object(region_names[i], "ec2_region", test_name, "no_issue_found"))
        return result

    def get_elastic_ip_in_use(self):
        result = []
        test_name = "aws_ec2_elastic_ip_in_use"

        response = self.aws_ec2_client.describe_addresses()
        addresses = response['Addresses']

        for address in addresses:
            public_ip = address['PublicIp']
            association_id = address.get('AssociationId')
            if association_id is not None:
                result.append(self._get_result_object(public_ip, "elastic_IP", test_name, "no_issue_found"))
            else:
                result.append(self._get_result_object(public_ip, "elastic_IP", test_name, "issue_found"))

        return result

    def get_unrestricted_mysql_access(self, all_inbound_permissions):
        result = []
        test_name = "aws_ec2_unrestricted_mysql_access"

        filtered_port = list(filter(lambda permission: (permission['IpProtocol'] == "-1")
                                    or ((permission['FromPort'] <= 3306 and permission['ToPort'] >= 3306) and permission['IpProtocol'] == 'tcp'), all_inbound_permissions))
        instances = list(map(lambda x: x['security_group'].id, list(filter(lambda permission: any([ip_range.get("CidrIp", "")
                         == "0.0.0.0/0" or ip_range.get("CidrIp", "") == "::/0" for ip_range in permission['IpRanges']]), filtered_port))))

        instances_with_issue = set(instances)
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)

        for instance in instances_with_issue:
            result.append(self._get_result_object(instance, "ec2_security_group", test_name, "issue_found"))
        for instance in instances_with_no_issue:
            result.append(self._get_result_object(instance, "ec2_security_group", test_name, "no_issue_found"))

        return result

    def detect_classic_ec2_instances(self):
        result = []
        test_name = "aws_ec2_detect_classic_ec2_instances"

        ec2_instances = self.ec2_instances

        for instance in ec2_instances:
            instance_id = instance['InstanceId']
            vpc_id = instance.get('VpcId')

            if vpc_id is not None:
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "no_issue_found"))
            else:
                result.append(self._get_result_object(instance_id, "ec2_instance", test_name, "issue_found"))

        return result

    def get_security_group_should_allow_access_to_specific_private_networks_only(self):
        test_name = "aws_ec2_security_group_should_allow_access_to_specific_private_networks_only"
        result = []
        security_groups = self.aws_ec2_client.describe_security_groups(Filters=[{'Name': 'ip-permission.cidr', 'Values': ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']}])
        instances_with_issue = set(list(map(lambda x: x['GroupId'], security_groups['SecurityGroups'])))
        instances_with_no_issue = self.set_security_group.difference(instances_with_issue)
        for i in instances_with_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "issue_found"))
        for i in instances_with_no_issue:
            result.append(self._get_result_object(i, "ec2_security_group", test_name, "no_issue_found"))
        return result

    def get_network_firewall_used(self):
        result = []
        test_name = "aws_ec2_network_firewall_used"

        paginator = self.aws_nfw_client.get_paginator('list_firewalls')
        response_iterator = paginator.paginate()
        firewalls = []
        for page in response_iterator:
            firewalls.extend(page['Firewalls'])

        if len(firewalls) > 0:
            for fw in firewalls:
                firewall_arn = fw['FirewallArn']
                response = self.aws_nfw_client.describe_firewall(FirewallArn=firewall_arn)
                firewall_details = response['Firewall']
                firewall_status = response['FirewallStatus']['Status']
                firewall_with_issue = False

                if firewall_status == 'PROVISIONING' or firewall_status == 'READY':
                    firewall_policy_arn = firewall_details.get('FirewallPolicyArn')

                    if firewall_policy_arn is not None:
                        response = self.aws_nfw_client.describe_firewall_policy(FirewallPolicyArn=firewall_policy_arn)
                        firewall_policy_status = response['FirewallPolicyResponse']['FirewallPolicyStatus']
                        firewall_rule_groups = []
                        if firewall_policy_status == 'ACTIVE':
                            firewall_policy = response['FirewallPolicy']

                            if firewall_policy.get('StatelessRuleGroupReferences') is not None:
                                firewall_rule_groups.extend(firewall_policy['StatelessRuleGroupReferences'])
                            else: pass

                            if firewall_policy.get('StatefulRuleGroupReferences') is not None:
                                firewall_rule_groups.extend(firewall_policy['StatefulRuleGroupReferences'])
                            else: pass

                            for rule in firewall_rule_groups:
                                rule_arn = rule['ResourceArn']
                                response = self.aws_nfw_client.describe_rule_group(RuleGroupArn=rule_arn)

                                rule_source = response['RuleGroup']['RulesSource']

                                state_full_rules = rule_source.get('StatefulRules')
                                state_less_rules = rule_source.get('StatelessRulesAndCustomActions')

                                if state_full_rules is not None:
                                    temp = list(filter(lambda x: x['Header']['Source'] == 'Any' or x['Header']['Destination'] == 'Any', state_full_rules))
                                    if len(temp) > 0:
                                        firewall_with_issue = True
                                        break
                                    else: pass
                                else: pass

                                if state_less_rules is not None:
                                    rules = state_less_rules['StatelessRules']
                                    for r in rules:
                                        attrs = r['RuleDefinition']['MatchAttributes']
                                        source_addresses = attrs['Sources']
                                        destination_addresses = attrs['Destinations']

                                        if any([i['AddressDefinition'] == '0.0.0.0/0' for i in source_addresses]) or any([i['AddressDefinition'] == '0.0.0.0/0' for i in destination_addresses]):
                                            firewall_with_issue: True
                                            break
                                        else: pass
                                else: pass

                            if firewall_with_issue:
                                result.append(self._get_result_object(firewall_arn, "aws_network_firewall", test_name, "issue_found"))
                            else:
                                result.append(self._get_result_object(firewall_arn, "aws_network_firewall", test_name, "no_issue_found"))

                        else: pass

                    else: pass

                else: pass
        else: pass

        return result
