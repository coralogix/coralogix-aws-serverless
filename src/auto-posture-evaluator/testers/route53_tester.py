import time
import boto3
import re
import ipaddress
import botocore.exceptions
import interfaces
import datetime as dt
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name: str):
        self.aws_region = region_name
        self.aws_route53_client = boto3.client('route53')
        self.aws_ec2_client = boto3.client('ec2')
        self.hosted_zones = self.aws_route53_client.list_hosted_zones()
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.route53_domains = []

    def declare_tested_service(self) -> str:
        return 'route53'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.aws_region.lower() == 'global':
            executor_list = []
            return_values = []
            self.route53_domains = self._get_all_route53_domains()

            if self.hosted_zones is not None and 'HostedZones' in self.hosted_zones:
                with ThreadPoolExecutor() as executor:
                    executor_list.append(executor.submit(self.detect_dangling_dns_records))
                    executor_list.append(executor.submit(self.route53_domain_expiry_in_7_days))
                    executor_list.append(executor.submit(self.detect_domain_is_not_locked_for_transfer))
                    executor_list.append(executor.submit(self.detect_domain_auto_renewal_disabled))
                    executor_list.append(executor.submit(self.detect_domain_expired))
                    executor_list.append(executor.submit(self.detect_dns_not_used))

                    for future in executor_list:
                        return_values.extend(future.result())
                return return_values

            else:
                raise Exception("No Route53 data could be retrieved.")
        else:
            return None

    def detect_dangling_dns_records(self):
        result = []
        test_name = "aws_route53_dangling_dns_records"
        # Filtering the list to get the list of public zones only
        public_zones = [zone for zone in self.hosted_zones['HostedZones'] if not zone['Config']['PrivateZone']]
        for cur_zone in public_zones:
            # Get all records in this zone
            zone_records = self.aws_route53_client.list_resource_record_sets(
                HostedZoneId=cur_zone['Id'],
                StartRecordName='.',
                StartRecordType='A'
            )['ResourceRecordSets']

            # Extract record names
            record_names = [record_name["Name"] for record_name in zone_records]

            # Get public IPs per DNS record
            for record in zone_records:
                record_name = record["Name"]
                dangling_ip_addresses = []
                registered_addresses = [record.get("ResourceRecords", []) for record in zone_records if record["Name"] == record_name][0]
                registered_ip_addresses = [resource_record["Value"] for resource_record in registered_addresses if re.match('\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}', str(resource_record["Value"]))]

                for registered_ip_address in registered_ip_addresses:
                    if ipaddress.ip_address(registered_ip_address).is_global:
                        try:
                            self.aws_ec2_client.describe_addresses(PublicIps=[registered_ip_address])
                        except botocore.exceptions.ClientError as ex:
                            if ex.response['Error']['Code'] == 'InvalidAddress.NotFound':
                                dangling_ip_addresses.append(registered_ip_address)
                            else:
                                raise ex

                if len(dangling_ip_addresses) > 0:
                    for dangling_ip_address in dangling_ip_addresses:
                        result.append({
                            "user": self.user_id,
                            "account_arn": self.account_arn,
                            "account": self.account_id,
                            "item": dangling_ip_address + "@@" + record_name,
                            "item_type": "dns_record",
                            "dns_record": record_name,
                            "record": record,
                            "test_name": test_name,
                            "dangling_ip": dangling_ip_address,
                            "zone": cur_zone["Id"],
                            "timestamp": time.time(),
                            "test_result": "issue_found"
                        })
                else:
                    result.append({
                        "user": self.user_id,
                        "account_arn": self.account_arn,
                        "account": self.account_id,
                        "test_name": test_name,
                        "item": record_name,
                        "item_type": "dns_record",
                        "record": record,
                        "timestamp": time.time(),
                        "test_result": "no_issue_found"
                    })

        return result

    def _append_route53_test_result(self, test_name, item, item_type, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "test_name": test_name,
            "item": item,
            "item_type": item_type,
            "timestamp": time.time(),
            "test_result": issue_status,
            "region": self.aws_region
        }

    def _get_all_aws_regions(self):
        all_regions = []
        client = boto3.client('ec2')
        response = client.describe_regions(AllRegions=True)

        for i in response['Regions']:
            all_regions.append(i['RegionName'])

        return all_regions

    def _get_all_route53_domains(self):
        domains = []

        aws_route53_domain_client = boto3.client('route53domains', region_name='us-east-1')
        paginator = aws_route53_domain_client.get_paginator('list_domains')
        response_iterator = paginator.paginate()
        for page in response_iterator:
            domains.extend(page['Domains'])
        return domains

    def route53_domain_expiry_in_7_days(self):
        result = []
        test_name = "aws_route53_domain_expiry_in_7_days"

        domains = self.route53_domains

        for domain in domains:
            domain_name = domain['DomainName']
            expiry_date = domain['Expiry']
            current_date = datetime.now(tz=dt.timezone.utc)

            time_diff = (expiry_date - current_date).days

            if time_diff > 7:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "no_issue_found"))
            else:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "issue_found"))

        return result

    def detect_domain_is_not_locked_for_transfer(self):
        result = []
        test_name = "aws_route53_domain_is_not_locked_for_transfer"

        domains = self.route53_domains

        for domain in domains:
            domain_name = domain['DomainName']
            transfer_lock = domain['TransferLock']

            if transfer_lock:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "no_issue_found"))
            else:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "issue_found"))

        return result

    def detect_domain_auto_renewal_disabled(self):
        result = []
        test_name = "aws_route53_domain_auto_renewal_disabled"

        domains = self.route53_domains

        for domain in domains:
            domain_name = domain['DomainName']
            auto_renew = domain['AutoRenew']

            if auto_renew:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "no_issue_found"))
            else:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "issue_found"))

        return result

    def detect_domain_expired(self):
        result = []
        test_name = "aws_route53_domain_expired"

        domains = self.route53_domains

        for domain in domains:
            domain_name = domain['DomainName']
            expiry = domain['Expiry']
            current_date = datetime.now(tz=dt.timezone.utc)

            if expiry <= current_date:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "issue_found"))
            else:
                result.append(self._append_route53_test_result(test_name, domain_name, "domain_name", "no_issue_found"))

        return result

    def detect_dns_not_used(self):
        test_name = "aws_route53_dns_not_used"
        result = []

        paginator = self.aws_route53_client.get_paginator('list_hosted_zones')
        response_iterator = paginator.paginate()
        hosted_zones = []
        for page in response_iterator:
            hosted_zones.extend(page['HostedZones'])

        item = "dns@@" + self.account_id
        if hosted_zones:
            result.append(self._append_route53_test_result(test_name, item, "dns_records", "no_issue_found"))
        else:
            result.append(self._append_route53_test_result(test_name, item, "dns_records", "issue_found"))

        return result
