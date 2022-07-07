import time
from concurrent.futures import ThreadPoolExecutor

import boto3
import interfaces


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name='global'):
        self.aws_cloudfront_client = boto3.client('cloudfront', region_name=region_name)
        self.cache = {}
        self.region_name = region_name
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.all_cloud_front_details = []

    def declare_tested_service(self) -> str:
        return 'cloudfront'

    def declare_tested_provider(self) -> str:
        return 'aws'

    def run_tests(self) -> list:
        if self.region_name != 'global':
            return None
        self.all_cloud_front_details = self._list_all_cloud_front()
        executor_list = []
        return_values = []

        with ThreadPoolExecutor() as executor:
            executor_list.append(executor.submit(self.detect_waf_enabled_disabled_distribution))
            executor_list.append(executor.submit(self.detect_unencrypted_cloudfront_to_origin_server_connection))
            executor_list.append(executor.submit(self.detect_encrypted_data_in_transit_using_tls_higher_version))
            executor_list.append(executor.submit(self.detect_unencrypted_cloudfront_to_viewer_connection))
            executor_list.append(executor.submit(
                self.detect_cloudfront_enable_origin_access_identity_for_cloudfront_distributions_with_s3_origin))

            for future in executor_list:
                return_values.extend(future.result())

        return return_values

    def _list_all_cloud_front(self):
        cloud_front_details = []
        response = self.aws_cloudfront_client.list_distributions(
            MaxItems='100'

        )
        if 'DistributionList' in response and response['DistributionList'] and 'Items' in response[
            'DistributionList'] and response['DistributionList'][
            'Items']:
            cloud_front_details.extend(response['DistributionList'][
                                           'Items'])
        if 'DistributionList' in response and response['DistributionList'] and 'IsTruncated' in response[
            'DistributionList'] and response['DistributionList']['IsTruncated']:
            while (response['DistributionList']['IsTruncated']):
                response = self.aws_cloudfront_client.list_distributions(
                    Marker=response['DistributionList']['NextMarker'],
                    MaxItems='100'

                )
                if 'DistributionList' in response and response['DistributionList'] and 'Items' in \
                        response['DistributionList'][
                            'Items']:
                    cloud_front_details.extend(response['DistributionList'][
                                                   'Items'])
        return cloud_front_details

    def _append_cloudfront_test_result(self, cloud_front_id, test_name, issue_status):
        return {
            "user": self.user_id,
            "account_arn": self.account_arn,
            "account": self.account_id,
            "timestamp": time.time(),
            "item": cloud_front_id,
            "item_type": "cloud_front",
            "test_name": test_name,
            "test_result": issue_status,
            "region": self.region_name
        }

    def detect_waf_enabled_disabled_distribution(self):
        waf_result = []
        test_name = 'aws_cloudfront_distribution_id_associated_with_a_waf_web_acl'
        for items_dict in self.all_cloud_front_details:
            if 'WebACLId' in items_dict and items_dict['WebACLId']:
                waf_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                      test_name,
                                                                      'no_issue_found'))
            else:
                waf_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                      test_name,
                                                                      'issue_found'))
        return waf_result

    def detect_unencrypted_cloudfront_to_origin_server_connection(self):
        protocol_result = []
        test_name = 'aws_cloudfront_unencrypted_cloudfront_to_origin_server_connection'
        for items_dict in self.all_cloud_front_details:
            issue_found = False
            for item_data_dict in items_dict['Origins']['Items']:
                if 'CustomOriginConfig' in item_data_dict and item_data_dict[
                    'CustomOriginConfig'] and 'OriginProtocolPolicy' in item_data_dict['CustomOriginConfig'] and \
                        item_data_dict['CustomOriginConfig']['OriginProtocolPolicy'] in ['http-only', 'match-viewer']:
                    issue_found = True
                    break
            if issue_found:
                protocol_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                           test_name,
                                                                           'issue_found'))
            else:
                protocol_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                           test_name,
                                                                           'no_issue_found'))
        return protocol_result

    def detect_encrypted_data_in_transit_using_tls_higher_version(self):
        tls_protocol_version_result = []
        test_name = 'aws_cloudfront_ensure_encrypted_data_in_transit_using_tls_1.2_protocol_or_higher'
        for items_dict in self.all_cloud_front_details:

            if 'ViewerCertificate' in items_dict and items_dict['ViewerCertificate'] and 'MinimumProtocolVersion' in \
                    items_dict['ViewerCertificate'] and items_dict['ViewerCertificate'][
                'MinimumProtocolVersion'] not in [
                'TLSv1.2_2018',
                'TLSv1.2_2019',
                'TLSv1.2_2021'
            ]:
                tls_protocol_version_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                                       test_name,
                                                                                       'issue_found'))
            else:
                tls_protocol_version_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                                       test_name,
                                                                                       'no_issue_found'))
        return tls_protocol_version_result

    def detect_unencrypted_cloudfront_to_viewer_connection(self):
        viewer_protocol_result = []
        test_name = 'aws_cloudfront_unencrypted_cloudfront_to_viewer_connection'
        for items_dict in self.all_cloud_front_details:
            if 'ViewerProtocolPolicy' in items_dict['DefaultCacheBehavior'] and items_dict['DefaultCacheBehavior'][
                'ViewerProtocolPolicy'] in ['allow-all',
                                            'redirect-to-https']:
                viewer_protocol_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                                  test_name,
                                                                                  'issue_found'))
            else:
                viewer_protocol_result.append(self._append_cloudfront_test_result(items_dict['Id'],
                                                                                  test_name,
                                                                                  'no_issue_found'))
        return viewer_protocol_result

    def detect_cloudfront_enable_origin_access_identity_for_cloudfront_distributions_with_s3_origin(self):
        result = []
        test_name = 'aws_cloudfront_enable_origin_access_identity_for_cloudfront_distributions_with_s3_origin'
        for items_dict in self.all_cloud_front_details:
            if 'Origins' in items_dict and 'Items' in items_dict['Origins'] and items_dict['Origins']['Items']:
                for origin_dict in items_dict['Origins']['Items']:
                    if 'S3OriginConfig' in origin_dict and (
                            ('OriginAccessIdentity' in origin_dict['S3OriginConfig']
                             and not origin_dict['S3OriginConfig'][
                                        'OriginAccessIdentity']) or not origin_dict[
                        'S3OriginConfig'] or 'OriginAccessIdentity' not in origin_dict['S3OriginConfig']):
                        result.append(
                            self._append_cloudfront_test_result(items_dict['Id'] + '@@' + origin_dict['Id'], test_name,
                                                                'issue_found'))
                    else:
                        result.append(
                            self._append_cloudfront_test_result(items_dict['Id'] + '@@' + origin_dict['Id'], test_name,
                                                                'no_issue_found'))

        return result

