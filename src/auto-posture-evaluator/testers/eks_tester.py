import time
from datetime import datetime, timezone
import boto3
import interfaces
import concurrent.futures




class Tester(interfaces.TesterInterface):
    def __init__(self, region_name):
        self.ssm = boto3.client('ssm')
        self.region_name = region_name
        self.aws_eks_client = boto3.client('eks', region_name=region_name)
        self.ec2_vpc_client = boto3.client('ec2', region_name=region_name)
        self.cache = {}
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.eks_cluster = []

    def declare_tested_service(self) -> str:
        return 'eks'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name == 'global' or self.region_name not in self._get_regions():
            return None
        self.eks_cluster = self._return_all_eks_cluster()
        executor_list = []
        return_value = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_eks_kubernetes_api_server_publicly_accessible))
            executor_list.append(executor.submit(self.detect_eks_control_plane_logging_is_disabled))
            executor_list.append(executor.submit(self.detect_eks_metric_and_alarm_do_not_exist_for_eks_configuration_changes))
            executor_list.append(executor.submit(self.detect_eks_outdated_ami_for_eks_related_instance))
            executor_list.append(executor.submit(self.detect_eks_unsupported_kubernetes_installed_on_eks_cluster))
            executor_list.append(executor.submit(self.detect_eks_default_vpc_is_being_used_to_launch_an_eks_cluster))
            executor_list.append(executor.submit(self.detect_eks_cluster_has_been_assigned_with_multiple_security_groups))
            executor_list.append(executor.submit(self.detect_eks_security_group_allows_incoming_traffic_on_forbidden_ports))
            executor_list.append(executor.submit(self.detect_eks_old_version_of_vpc_cni_installed_on_eks_cluster))
            executor_list.append(executor.submit(self.detect_eks_cluster_secrets_are_not_encrypted))
            executor_list.append(executor.submit(self.detect_eks_cluster_without_fargate_profiles))
            executor_list.append(executor.submit(self.detect_eks_node_with_public_ip_address))

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

    def _return_all_eks_cluster(self):
        eks_cluster_response = self.aws_eks_client.list_clusters(
            maxResults=100
        )
        eks_cluster_list = eks_cluster_response['clusters']
        while 'nextToken' in eks_cluster_response and eks_cluster_response['nextToken']:
            eks_cluster_response = self.aws_eks_client.list_clusters(
                maxResults=100,
                nextToken=eks_cluster_response['nextToken']
            )
            eks_cluster_list.append(eks_cluster_response['clusters'])
        eks_cluster_describtion = [self.aws_eks_client.describe_cluster(name=eks_cluster)['cluster'] for eks_cluster in
                                   eks_cluster_list]
        return eks_cluster_describtion

    def _append_eks_test_result(self, eks, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": eks['name'],
            "item_type": "eks",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def detect_eks_kubernetes_api_server_publicly_accessible(self):
        publicly_accessible = []
        test_name = 'aws_eks_kubernetes_api_server_publicly_accessible'
        for eks_data in self.eks_cluster:
            if 'resourcesVpcConfig' in eks_data and 'endpointPublicAccess' in eks_data['resourcesVpcConfig'] and \
                    eks_data['resourcesVpcConfig']['endpointPublicAccess']:
                # issue found
                publicly_accessible.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                publicly_accessible.append(self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return publicly_accessible

    def detect_eks_control_plane_logging_is_disabled(self):
        control_plane = []
        test_name = 'aws_eks_control_plane_logging_is_disabled'
        for eks_data in self.eks_cluster:
            issue_found = True
            if 'logging' in eks_data and 'clusterLogging' in eks_data['logging'] and eks_data['logging'][
                'clusterLogging']:
                for cluster_logging_dict in eks_data['logging']['clusterLogging']:
                    if 'types' in cluster_logging_dict and cluster_logging_dict[
                        'types'] and 'enabled' in cluster_logging_dict and cluster_logging_dict[
                        'enabled']:
                        issue_found = False
                        break
            if issue_found:
                control_plane.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                control_plane.append(self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))
        return control_plane

    def detect_eks_metric_and_alarm_do_not_exist_for_eks_configuration_changes(self):
        metric_and_alarm_result = []
        test_name = 'aws_eks_metric_and_alarm_do_not_exist_for_eks_configuration_changes'
        for eks_data in self.eks_cluster:
            issue_found = True
            for cluster_logging_dict in eks_data['logging']['clusterLogging']:
                if 'types' in cluster_logging_dict and cluster_logging_dict[
                    'types'] and 'enabled' in cluster_logging_dict and cluster_logging_dict[
                    'enabled'] and 'audit' in cluster_logging_dict['types']:
                    issue_found = False
                    break
            if issue_found:
                metric_and_alarm_result.append(
                    self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                metric_and_alarm_result.append(
                    self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return metric_and_alarm_result

    def detect_eks_outdated_ami_for_eks_related_instance(self):
        eks_ami_result = []
        test_name = 'aws_eks_outdated_ami_for_eks_related_instance'
        for eks_data in self.eks_cluster:
            issue_found = False
            nodegroups_response = self.aws_eks_client.list_nodegroups(
                clusterName=eks_data['name'],
                maxResults=100)
            if 'nodegroups' in nodegroups_response and nodegroups_response['nodegroups']:
                for node_group_name in nodegroups_response['nodegroups']:
                    response = self.aws_eks_client.describe_nodegroup(
                        clusterName=eks_data['name'],
                        nodegroupName=node_group_name
                    )
                    if 'nodegroup' in response and 'releaseVersion' in response['nodegroup'] and response['nodegroup'][
                        'releaseVersion'] and response['nodegroup'][
                                                  'releaseVersion'][:3] == 'ami':
                        ami_image_response = self.ec2_vpc_client.describe_images(
                            ImageIds=[response['nodegroup']['releaseVersion']],
                        )
                        if 'Images' in ami_image_response and ami_image_response['Images'] \
                                and 'DeprecationTime' in ami_image_response['Images'][0] \
                                and ami_image_response['Images'][0]['DeprecationTime'] and datetime.now(timezone.utc) > \
                                datetime.fromisoformat(
                                    ami_image_response['Images'][0]['DeprecationTime'][0:-1] + '+00:00'):
                            issue_found = True
                            break
            if issue_found:
                eks_ami_result.append(
                    self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                eks_ami_result.append(
                    self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return eks_ami_result

    def detect_eks_unsupported_kubernetes_installed_on_eks_cluster(self):
        unsupported_eks = []
        supported_versions = [1.22, 1.21, 1.20, 1.19]
        test_name = 'aws_eks_unsupported_kubernetes_installed_on_eks_cluster'
        for eks_data in self.eks_cluster:
            if 'version' in eks_data and float(eks_data['version']) not in supported_versions:
                unsupported_eks.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                unsupported_eks.append(self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))
        return unsupported_eks

    def detect_eks_default_vpc_is_being_used_to_launch_an_eks_cluster(self):
        eks_default_vpc = []
        test_name = 'aws_eks_default_vpc_is_being_used_to_launch_an_eks_cluster'
        default_vpc = []
        for eks_data in self.eks_cluster:
            if eks_data['resourcesVpcConfig']['vpcId'] in default_vpc:
                eks_default_vpc.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                vpc_response = self.ec2_vpc_client.describe_vpcs(VpcIds=[eks_data['resourcesVpcConfig']['vpcId']])
                if vpc_response['Vpcs'][0]['IsDefault']:
                    default_vpc.append(eks_data['resourcesVpcConfig']['vpcId'])
                    eks_default_vpc.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
                else:
                    eks_default_vpc.append(self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))
        return eks_default_vpc

    def detect_eks_cluster_has_been_assigned_with_multiple_security_groups(self):
        multiple_security_groups = []
        test_name = 'aws_eks_cluster_has_been_assigned_with_multiple_security_groups'
        for eks_data in self.eks_cluster:
            if 'resourcesVpcConfig' in eks_data and 'securityGroupIds' in eks_data['resourcesVpcConfig'] and len(
                    eks_data['resourcesVpcConfig']['securityGroupIds']) > 1:
                multiple_security_groups.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                multiple_security_groups.append(self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return multiple_security_groups

    def detect_eks_security_group_allows_incoming_traffic_on_forbidden_ports(self):
        incoming_traffic_on_forbidden_ports = []
        test_name = 'aws_eks_security_group_allows_incoming_traffic_on_forbidden_ports'
        for eks_data in self.eks_cluster:
            issue_found = False
            if 'resourcesVpcConfig' in eks_data and 'securityGroupIds' in eks_data['resourcesVpcConfig'] and len(
                    eks_data['resourcesVpcConfig']['securityGroupIds']):
                for security_group_id in eks_data['resourcesVpcConfig']['securityGroupIds']:
                    security_groups_response = self.ec2_vpc_client.describe_security_groups(
                        Filters=[
                            {
                                'Name': 'group-id',
                                'Values': [
                                    security_group_id,
                                ]
                            },
                        ])
                    if 'SecurityGroups' in security_groups_response and security_groups_response[
                        'SecurityGroups']:
                        for security_group_dict in security_groups_response['SecurityGroups']:
                            for ip_permissions_dict in security_group_dict['IpPermissions']:
                                if not ('FromPort' in ip_permissions_dict and ip_permissions_dict[
                                    'FromPort'] and 'ToPort' in ip_permissions_dict and ip_permissions_dict[
                                            'ToPort'] and \
                                        ip_permissions_dict['ToPort'] == ip_permissions_dict['FromPort'] and \
                                        ip_permissions_dict['FromPort'] in [
                                            443] and 'IpProtocol' in ip_permissions_dict and \
                                        ip_permissions_dict['IpProtocol'] == 'tcp'):
                                    issue_found = True
                                    break
                            if issue_found:
                                break
                    if issue_found:
                        break
            if issue_found:
                incoming_traffic_on_forbidden_ports.append(
                    self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                incoming_traffic_on_forbidden_ports.append(
                    self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return incoming_traffic_on_forbidden_ports

    def detect_eks_old_version_of_vpc_cni_installed_on_eks_cluster(self):
        vpc_cni_installed_version_result = []
        test_name = 'aws_eks_old_version_of_vpc_cni_installed_on_eks_cluster'
        for eks_data in self.eks_cluster:
            # this will get all the addon-versions for based on the kubernetes version
            available_addon_versions = self.aws_eks_client.describe_addon_versions(
                kubernetesVersion=eks_data['version'],
                maxResults=100,
                addonName='vpc-cni'
            )
            latest_addon_version = available_addon_versions['addons'][0]['addonVersions'][0]['addonVersion']
            try:
                describe_addon_response = self.aws_eks_client.describe_addon(
                    clusterName=eks_data['name'],
                    addonName='vpc-cni'
                )
                if 'addon' in describe_addon_response and 'addonVersion' in describe_addon_response['addon'] and \
                        describe_addon_response['addon']['addonVersion'] == latest_addon_version:
                    vpc_cni_installed_version_result.append(
                        self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))
                else:
                    vpc_cni_installed_version_result.append(
                        self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            except:
                vpc_cni_installed_version_result.append(
                    self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return vpc_cni_installed_version_result

    def detect_eks_cluster_secrets_are_not_encrypted(self):
        eks_cluster_secrets = []
        test_name = 'aws_eks_cluster_secrets_are_not_encrypted'
        for eks_data in self.eks_cluster:
            issue_found = True
            if 'encryptionConfig' in eks_data and eks_data['encryptionConfig']:
                for encryption_config_dict in eks_data['encryptionConfig']:
                    if 'provider' in encryption_config_dict and 'keyArn' in encryption_config_dict['provider'] and \
                            encryption_config_dict['provider']['keyArn']:
                        issue_found = False
                        break
            if issue_found:
                eks_cluster_secrets.append(self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                eks_cluster_secrets.append(self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))

        return eks_cluster_secrets

    def detect_eks_cluster_without_fargate_profiles(self):
        eks_cluster_fargate_profiles_list = []
        test_name = 'aws_eks_cluster_without_fargate_profiles'
        for eks_data in self.eks_cluster:
            fargate_profiles_response = self.aws_eks_client.list_fargate_profiles(
                clusterName=eks_data['name']
            )
            if 'fargateProfileNames' in fargate_profiles_response and fargate_profiles_response['fargateProfileNames']:
                eks_cluster_fargate_profiles_list.append(
                    self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))
            else:
                eks_cluster_fargate_profiles_list.append(
                    self._append_eks_test_result(eks_data, test_name, 'issue_found'))

        return eks_cluster_fargate_profiles_list

    def detect_eks_node_with_public_ip_address(self):
        node_with_public_ip_check = []
        test_name = 'aws_eks_node_with_public_ip_address'
        for eks_data in self.eks_cluster:
            issue_found = False
            nodegroups_response = self.aws_eks_client.list_nodegroups(
                clusterName=eks_data['name'],
                maxResults=100)
            if 'nodegroups' in nodegroups_response and nodegroups_response['nodegroups']:
                for node_group_name in nodegroups_response['nodegroups']:
                    node_group_detail = self.aws_eks_client.describe_nodegroup(
                        clusterName=eks_data['name'],
                        nodegroupName=node_group_name
                    )
                    subnetid = 'nodegroup' in node_group_detail and 'subnets' in node_group_detail[
                        'nodegroup'] and node_group_detail['nodegroup']['subnets'] or []
                    route_tables_response = self.ec2_vpc_client.describe_route_tables(
                        Filters=[
                            {
                                'Name': 'vpc-id',
                                'Values': [eks_data['resourcesVpcConfig']['vpcId']]
                            }
                        ])
                    for routeTable in route_tables_response['RouteTables']:
                        associations = routeTable['Associations']
                        routes = routeTable['Routes']
                        isPublic = False
                        for route in routes:
                            gid = route.get('GatewayId', '')
                            if gid.startswith('igw-'):
                                isPublic = True
                        if (not isPublic):
                            continue
                        for assoc in associations:
                            subnetId = assoc.get('SubnetId', None)
                            if subnetId in subnetid:
                                issue_found = True
                                break
                        if issue_found:
                            break
                    if issue_found:
                        break
            if issue_found:
                node_with_public_ip_check.append(
                    self._append_eks_test_result(eks_data, test_name, 'issue_found'))
            else:
                node_with_public_ip_check.append(
                    self._append_eks_test_result(eks_data, test_name, 'no_issue_found'))
        return node_with_public_ip_check

