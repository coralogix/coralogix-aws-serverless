import os
import time
import jmespath
import interfaces
import boto3
from botocore.exceptions import ClientError
import datetime as dt
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class Tester(interfaces.TesterInterface):
    def __init__(self, region_name: str) -> None:
        self.aws_iam_client = boto3.client('iam')
        self.aws_iam_resource = boto3.resource('iam')
        self.aws_access_analyzer_client = boto3.client('accessanalyzer')
        self.aws_region = region_name
        self.user_id = boto3.client('sts').get_caller_identity().get('UserId')
        self.account_arn = boto3.client('sts').get_caller_identity().get('Arn')
        self.account_id = boto3.client('sts').get_caller_identity().get('Account')
        self.iam_user_credentials_unuse_threshold = os.environ.get('AUTOPOSTURE_IAM_CREDENTIALS_UNUSE_THRESHOLD')
        self.password_maximum_age_policy = os.environ.get('AUTOPOSTURE_PASSWORD_MAX_AGE_POLICY')
        self.password_length_threshold_policy = os.environ.get('AUTOPOSTURE_PASSWORD_LENGTH_THRESHOLD_POLICY')
        self.access_key_maximum_age = os.environ.get('AUTOPOSTURE_ACCESS_KEY_MAX_AGE')
        self.iam_users = self._get_all_iam_users()

    def declare_tested_provider(self) -> str:
        return 'aws'

    def declare_tested_service(self) -> str:
        return 'iam'

    def run_tests(self) -> list:

        if self.aws_region.lower() == 'global':
            executor_list = []
            return_values = []

            with ThreadPoolExecutor() as executor:
                executor_list.append(executor.submit(self.get_password_policy_has_14_or_more_char))
                executor_list.append(executor.submit(self.get_hw_mfa_enabled_for_root_account))
                executor_list.append(executor.submit(self.get_mfa_enabled_for_root_account))
                executor_list.append(executor.submit(self.get_policy_does_not_have_user_attached))
                executor_list.append(executor.submit(self.get_access_keys_rotated_every_90_days))
                executor_list.append(executor.submit(self.get_server_certificate_will_expire))
                executor_list.append(executor.submit(self.get_expired_ssl_tls_certtificate_removed))
                executor_list.append(executor.submit(self.get_password_expires_in_90_days))
                executor_list.append(executor.submit(self.get_password_policy_requires_lowercase))
                executor_list.append(executor.submit(self.get_password_policy_requires_uppercase))
                executor_list.append(executor.submit(self.get_password_policy_requires_symbols))
                executor_list.append(executor.submit(self.get_password_policy_requires_numbers))
                executor_list.append(executor.submit(self.get_support_role_for_aws_support))
                executor_list.append(executor.submit(self.get_priviledged_user_has_admin_permissions))
                executor_list.append(executor.submit(self.get_password_reuse_policy))
                executor_list.append(executor.submit(self.get_no_access_key_for_root_account))
                executor_list.append(executor.submit(self.get_mfa_enabled_for_all_iam_users))
                executor_list.append(executor.submit(self.get_role_uses_trused_principals))
                executor_list.append(executor.submit(self.get_access_keys_are_not_created_during_initial_setup))
                executor_list.append(executor.submit(self.get_policy_with_admin_privilege_not_created))
                executor_list.append(executor.submit(self.get_iam_user_credentials_unused_for_45_days))
                executor_list.append(executor.submit(self.get_more_than_one_active_access_key_for_a_single_user))
                executor_list.append(executor.submit(self.get_iam_access_analyzer_disabled))
                executor_list.append(executor.submit(self.get_iam_pre_heartbleed_server_certificates))
                executor_list.append(executor.submit(self.get_user_access_keys))
                executor_list.append(executor.submit(self.detect_no_iam_user_present))

                for future in executor_list:
                    return_values.extend(future.result())

            return return_values
        else:
            return None

    def _get_all_iam_users(self):
        users = []
        paginator = self.aws_iam_client.get_paginator('list_users')
        response_iterator = paginator.paginate()

        for page in response_iterator:
            users.extend(page['Users'])

        return users

    def _append_iam_test_result(self, item, item_type, test_name, issue_status):
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

    def get_password_policy_has_14_or_more_char(self):
        result = []
        test_name = "aws_iam_password_has_14_or_more_characters"
        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']

            password_length_threshold = int(self.password_length_threshold_policy) if self.password_length_threshold_policy else 14
            if password_policy['MinimumPasswordLength'] >= password_length_threshold:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        return result

    def get_hw_mfa_enabled_for_root_account(self):
        result = []
        test_name = "aws_iam_hardware_mfa_enabled_for_root_account"

        response = self.aws_iam_client.list_virtual_mfa_devices(AssignmentStatus='Assigned')
        virtual_devices = response['VirtualMFADevices']

        if len(virtual_devices) > 0:
            for device in virtual_devices:
                serial_number = device['SerialNumber']
                root_account_device = serial_number.split('/')[-1]

                if root_account_device == 'root-account-mfa-device':
                    result.append(self._append_iam_test_result("account_summary@@" + self.account_id, "account_summary_record", test_name, "no_issue_found"))
                else:
                    result.append(self._append_iam_test_result("account_summary@@" + self.account_id, "account_summary_record", test_name, "issue_found"))
        else: pass
        return result

    def get_mfa_enabled_for_root_account(self):
        result = []
        test_name = "aws_iam_mfa_is_enabled_for_root_account"

        response = self.aws_iam_client.get_account_summary()
        account_summary = response['SummaryMap']
        if account_summary['AccountMFAEnabled']:
            result.append(self._append_iam_test_result("account_summary@@" + self.account_id, "account_summary_record", test_name, "no_issue_found"))
        else:
            result.append(self._append_iam_test_result("account_summary@@" + self.account_id, "account_summary_record", test_name, "issue_found"))
        return result

    def get_policy_does_not_have_user_attached(self):
        result = []
        test_name = "aws_iam_policy_does_not_have_a_user_attached_to_it"
        policies = []
        can_paginate = self.aws_iam_client.can_paginate('list_policies')
        if can_paginate:
            paginator = self.aws_iam_client.get_paginator('list_policies')
            response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50})

            for page in response_iterator:
                policies.extend(page['Policies'])
        else:
            response = self.aws_iam_client.list_policies()
            policies.extend(response['Policies'])

        for policy in policies:
            policy_id = policy['PolicyId']
            policy_arn = policy['Arn']
            response = self.aws_iam_client.list_entities_for_policy(PolicyArn=policy_arn, EntityFilter='User')

            attached_users = response['PolicyUsers']
            if len(attached_users) > 0:
                result.append(self._append_iam_test_result(policy_id, "iam_policy", test_name, "issue_found"))
            else:
                result.append(self._append_iam_test_result(policy_id, "iam_policy", test_name, "no_issue_found"))

        return result

    def get_access_keys_rotated_every_90_days(self):
        result = []
        test_name = "aws_iam_access_keys_are_rotated_every_90_days_or_less"

        users = self.iam_users
        access_keys_max_age = int(self.access_key_maximum_age) if self.access_key_maximum_age else 90
        current_date = datetime.now(tz=dt.timezone.utc)
        if len(users) > 0:
            for user in users:
                user_name = user['UserName']
                response = self.aws_iam_client.list_access_keys(UserName=user_name)
                access_keys = response['AccessKeyMetadata']
                old_access_keys = 0
                for key in access_keys:
                    create_date = key['CreateDate']
                    time_diff = (current_date - create_date).days

                    if time_diff > access_keys_max_age:
                        old_access_keys += 1
                    else: pass
                if old_access_keys > 0:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
                else:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
        else: pass
        return result

    def get_server_certificate_will_expire(self):
        result = []
        test_name = "aws_iam_server_certificate_will_expire_within_30_days"

        paginator = self.aws_iam_client.get_paginator('list_server_certificates')
        response_iterator = paginator.paginate()
        certificates = []
        for page in response_iterator:
            certificates.extend(page['ServerCertificateMetadataList'])
        current_date = datetime.date(datetime.now())
        if len(certificates) > 0:

            for certificate in certificates:
                certificate_id = certificate['ServerCertificateId']
                expiration_date = datetime.date(certificate['Expiration'])
                time_diff = (expiration_date - current_date).days
                if time_diff < 0:
                    result.append(self._append_iam_test_result(certificate_id, "iam_server_certificate", test_name, "issue_found"))
                elif time_diff <= 30:
                    result.append(self._append_iam_test_result(certificate_id, "iam_server_certificate", test_name, "issue_found"))
                else:
                    result.append(self._append_iam_test_result(certificate_id, "iam_server_certificate", test_name, "no_issue_found"))
        else: pass

        return result

    def get_expired_ssl_tls_certtificate_removed(self):
        result = []
        test_name = "aws_iam_all_expired_ssl_tls_certificate_removed"

        paginator = self.aws_iam_client.get_paginator('list_server_certificates')
        response_iterator = paginator.paginate()
        certificates = []
        for page in response_iterator:
            certificates.extend(page['ServerCertificateMetadataList'])
        current_date = datetime.date(datetime.now())
        if len(certificates) > 0:
            for certificate in certificates:
                certificate_id = certificate['ServerCertificateId']
                expiration_date = datetime.date(certificate['Expiration'])
                time_diff = (expiration_date - current_date).days
                if time_diff < 0:
                    result.append(self._append_iam_test_result(certificate_id, "iam_server_certificate", test_name, "issue_found"))
                else:
                    result.append(self._append_iam_test_result(certificate_id, "iam_server_certificate", test_name, "no_issue_found"))
        else: pass

        return result

    def get_password_expires_in_90_days(self):
        result = []
        test_name = "aws_iam_policy_is_set_expire_passwords_within_90_days_or_less"

        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']

            password_maximum_age_policy = int(self.password_maximum_age_policy) if self.password_maximum_age_policy else 90
            expire_passwords = password_policy.get('ExpirePasswords')
            if expire_passwords:
                max_password_age = password_policy['MaxPasswordAge']
                if max_password_age <= password_maximum_age_policy:
                    result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
                else:
                    result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("no_password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        return result

    def get_password_policy_requires_lowercase(self):
        result = []
        test_name = "aws_iam_password_requires_one_or_more_lowercase_characters"

        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']

            if password_policy['RequireLowercaseCharacters']:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("no_password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        return result

    def get_password_policy_requires_uppercase(self):
        result = []
        test_name = "aws_iam_password_requires_one_or_more_uppercase_characters"

        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']

            if password_policy['RequireUppercaseCharacters']:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("no_password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        return result

    def get_password_policy_requires_symbols(self):
        result = []
        test_name = "aws_iam_password_requires_one_or_more_symbols"
        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']

            if password_policy['RequireSymbols']:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("no_password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        return result

    def get_password_policy_requires_numbers(self):
        result = []
        test_name = "aws_iam_password_requires_one_or_more_numbers"

        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']

            if password_policy['RequireNumbers']:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))

        return result

    def get_support_role_for_aws_support(self):
        result = []
        policies = []
        test_name = "aws_iam_support_role_to_manage_incidents_with_AWS_support"

        paginator = self.aws_iam_client.get_paginator('list_policies')
        response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50})

        for page in response_iterator:
            policies.extend(page['Policies'])

        policy_dict = {'policies': policies}
        response = jmespath.search("policies[?PolicyName == 'AWSSupportAccess'].Arn[]", policy_dict)
        policy_arn = response[0]
        if len(response) > 0:
            response = self.aws_iam_client.list_entities_for_policy(
                PolicyArn=policy_arn,
                EntityFilter='Role'
            )
            support_role = response['PolicyRoles']
            if len(support_role) > 0:
                result.append(self._append_iam_test_result("support_role@@" + self.account_id, "iam_support_role", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("support_role@@" + self.account_id, "iam_support_role", test_name, "issue_found"))
        else: pass

        return result

    def get_priviledged_user_has_admin_permissions(self):
        result = []
        test_name = "aws_iam_priviledged_user_has_admin_permissions"

        users = self.iam_users

        if len(users) > 0:
            for user in users:
                user_name = user['UserName']
                policies = []
                paginator = self.aws_iam_client.get_paginator('list_attached_user_policies')
                response_iterator = paginator.paginate(UserName=user_name)

                for page in response_iterator:
                    policies.extend(page['AttachedPolicies'])
                policies = list(map(lambda x: x['PolicyName'], policies))
                admin_access = list(filter(lambda x: 'AdministratorAccess' in x, policies))

                if admin_access:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
                else:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
        else: pass

        return result

    def get_password_reuse_policy(self):
        result = []
        test_name = "aws_iam_password_policy_prevents_password_reuse"

        try:
            response = self.aws_iam_client.get_account_password_policy()
            password_policy = response['PasswordPolicy']
            password_reuse_prevetion = password_policy.get('PasswordReusePrevention')

            if password_reuse_prevetion is not None:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "no_issue_found"))
            else:
                result.append(self._append_iam_test_result("password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        except self.aws_iam_client.exceptions.NoSuchEntityException:
            result.append(self._append_iam_test_result("no_password_policy@@" + self.account_id, "password_policy_record", test_name, "issue_found"))
        return result

    def get_no_access_key_for_root_account(self):
        result = []
        test_name = "aws_iam_no_root_account_access_key_exists"

        response = self.aws_iam_client.get_account_summary()
        root_access_key_present = response['SummaryMap']['AccountAccessKeysPresent']

        if root_access_key_present:
            result.append(self._append_iam_test_result("root_account@@" + self.account_id, "iam_root_account", test_name, "issue_found"))
        else:
            result.append(self._append_iam_test_result("root_account@@" + self.account_id, "iam_root_account", test_name, "no_issue_found"))

        return result

    def get_mfa_enabled_for_all_iam_users(self):
        result = []
        users = self.iam_users
        test_name = "aws_iam_mfa_is_enabled_for_all_users_with_console_password"

        if len(users) > 0:
            for user in users:
                user_name = user['UserName']
                paginator = self.aws_iam_client.get_paginator('list_mfa_devices')
                response_paginator = paginator.paginate(UserName=user_name)
                mfa_devices = []

                for page in response_paginator:
                    mfa_devices.extend(page['MFADevices'])

                if len(mfa_devices) > 0:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
                else:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
        else: pass

        return result

    def get_role_uses_trused_principals(self):
        result = []
        test_name = "aws_iam_role_uses_trusted_principals"

        paginator = self.aws_iam_client.get_paginator('list_roles')
        response_iterator = paginator.paginate()
        roles = []
        for page in response_iterator:
            roles.extend(page['Roles'])

        for r in roles:
            role_name = r['RoleName']
            assume_role_policy = r['AssumeRolePolicyDocument']
            statements = assume_role_policy['Statement']

            if any([statement['Principal'] == '*' or statement['Principal'] == {"AWS": "*"} for statement in statements]):
                result.append(self._append_iam_test_result(role_name, "iam_role", test_name, "issue_found"))
            else:
                result.append(self._append_iam_test_result(role_name, "iam_role", test_name, "issue_found"))

        return result

    def get_access_keys_are_not_created_during_initial_setup(self):
        result = []
        test_name = "aws_iam_access_keys_are_not_created_for_user_during_initial_setup"
        users = self.iam_users

        if len(users) > 0:
            for user in users:
                user_name = user['UserName']
                user_created_at = user['CreateDate']
                response = self.aws_iam_client.list_access_keys(UserName=user_name)
                access_key_metadata = response['AccessKeyMetadata']

                if len(access_key_metadata) > 0:
                    for access_key in access_key_metadata:
                        access_key_created_at = access_key['CreateDate']
                        access_key_status = access_key['Status']

                        issue_with_access_key = False
                        if access_key_status == 'Active':
                            user_created_at = datetime.strptime(datetime.strftime(user_created_at, '%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M')
                            access_key_created_at = datetime.strptime(datetime.strftime(access_key_created_at, '%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M')

                            if user_created_at == access_key_created_at:
                                issue_with_access_key = True
                                break
                            else: pass
                        else: pass

                    if issue_with_access_key:
                        result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
                    else:
                        result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
                else:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
        else: pass

        return result

    def get_policy_with_admin_privilege_not_created(self):
        result = []
        policies = []
        test_name = "aws_iam_policy_with_admin_privilege_not_created"

        paginator = self.aws_iam_client.get_paginator('list_policies')
        response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50})

        for page in response_iterator:
            policies.extend(page['Policies'])

        for policy in policies:
            policy_id = policy['PolicyId']
            policy_arn = policy['Arn']
            version_id = policy['DefaultVersionId']

            response = self.aws_iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=version_id)
            policy_document = response['PolicyVersion']['Document']['Statement']

            for policy in policy_document:
                if (type(policy) is not dict or not policy.get('Action')): continue
                if ((policy.get('Resource') and (policy['Resource'] == '*' and policy['Action'] == '*'))
                    or (type(policy['Action']) is str and policy['Action'] == '*:*')
                        or (type(policy['Action']) is list and any([True if action == '*:*' else False for action in policy['Action']]))):
                    result.append(self._append_iam_test_result(policy_id, "iam_policy", test_name, "issue_found"))
                else:
                    result.append(self._append_iam_test_result(policy_id, "iam_policy", test_name, "no_issue_found"))
        return result

    def get_iam_user_credentials_unused_for_45_days(self):
        result = []
        users = self.iam_users
        test_name = "aws_iam_user_credentials_unused_for_45_days_or_more"

        credentials_unuse_threshold = int(self.iam_user_credentials_unuse_threshold) if self.iam_user_credentials_unuse_threshold else 45
        current_date = datetime.now(tz=dt.timezone.utc)
        if len(users) > 0:
            for user in users:
                user_name = user['UserName']
                password_last_used = user.get('PasswordLastUsed')
                if password_last_used is not None:
                    time_diff = (current_date - password_last_used).days
                    if time_diff >= credentials_unuse_threshold:
                        result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
                    else:
                        result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
                else:
                    try:
                        response = self.aws_iam_client.get_login_profile(UserName=user_name)
                        create_date = response['LoginProfile']['CreateDate']
                        time_diff = (current_date - create_date).days

                        if time_diff >= credentials_unuse_threshold:
                            result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
                        else:
                            result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
                    except ClientError:
                        # no login profile -> programmatic user
                        response = self.aws_iam_client.list_access_keys(UserName=user_name)
                        access_keys = {'access_keys': response['AccessKeyMetadata']}
                        access_keys = jmespath.search("access_keys[?Status=='Active']", access_keys)

                        key_used = []
                        for i in access_keys:
                            access_key_id = i['AccessKeyId']
                            create_date = i['CreateDate']

                            response = self.aws_iam_client.get_access_key_last_used(AccessKeyId=access_key_id)
                            access_key_last_used = response['AccessKeyLastUsed']
                            last_used_date = access_key_last_used.get('LastUsedDate')
                            if last_used_date is not None:
                                key_used.append(last_used_date)
                            else: key_used.append(create_date)

                        r = list(map(lambda x: (current_date - x).days, key_used))
                        if any([i >= credentials_unuse_threshold for i in r]):
                            result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
                        else:
                            result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
        else: pass

        return result

    def get_more_than_one_active_access_key_for_a_single_user(self):
        result = []
        users = self.iam_users
        test_name = "aws_iam_more_than_one_active_access_key_for_a_single_user"

        for user in users:
            user_name = user['UserName']
            response = self.aws_iam_client.list_access_keys(UserName=user_name)

            access_keys = {'access_keys': response['AccessKeyMetadata']}
            response = jmespath.search("access_keys[?Status=='Active'].AccessKeyId", access_keys)

            if len(response) > 1:
                result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
            else:
                result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))

        return result

    def get_iam_access_analyzer_disabled(self):
        result = []
        test_name = "aws_iam_access_analyzer_is_disabled"

        response = self.aws_access_analyzer_client.list_analyzers()
        analyzers = {"analyzer": response['analyzers']}

        query_result = jmespath.search("analyzer[?status=='ACTIVE'].arn", analyzers)
        if len(query_result) > 0:
            result.append(self._append_iam_test_result("access_analyzers@@" + self.account_id, "iam_access_analyzers", test_name, "no_issue_found"))
        else:
            result.append(self._append_iam_test_result("no_access_analyzers@@" + self.account_id, "iam_access_analyzers", test_name, "issue_found"))

        return result

    def get_iam_pre_heartbleed_server_certificates(self):
        result = []
        test_name = "aws_iam_pre_heartbleed_server_certificates"
        certificates = []
        can_paginate = self.aws_iam_client.can_paginate('list_server_certificates')
        if can_paginate:
            paginator = self.aws_iam_client.get_paginator('list_server_certificates')
            response_iterator = paginator.paginate(PaginationConfig={'PageSize': 50})
            for page in response_iterator:
                certificates.extend(page['ServerCertificateMetadataList'])
        else:
            response = self.aws_iam_client.list_server_certificates()
            certificates.extend(response['ServerCertificateMetadataList'])

        for certificate in certificates:
            name = certificate["ServerCertificateName"]
            issue_found = False
            upload_date = certificate['UploadDate']

            if upload_date.year < 2014 or (upload_date.year == 2014 and upload_date.month < 4):
                issue_found = True
            if issue_found:
                result.append(self._append_iam_test_result(name, "server_certificate", test_name, "issue_found"))
            else:
                result.append(self._append_iam_test_result(name, "server_certificate", test_name, "no_issue_found"))
        return result

    def get_user_access_keys(self):
        result = []
        users = self.iam_users
        test_name = "aws_iam_there_is_atleast_one_user_with_access_keys_for_api_access"

        if len(users) > 0:
            for user in users:
                user_name = user["UserName"]
                response = self.aws_iam_client.list_access_keys(UserName=user_name)
                access_keys = response["AccessKeyMetadata"]
                temp = list(filter(lambda x: x["Status"] == "Active", access_keys))

                if len(temp) >= 1:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "no_issue_found"))
                else:
                    result.append(self._append_iam_test_result(user_name, "iam_user", test_name, "issue_found"))
        else: pass

        return result

    def detect_no_iam_user_present(self):
        result = []
        test_name = "aws_iam_atleast_one_user_is_present_to_access_aws_account"
        users = self.iam_users

        if len(users) >= 1:
            result.append(self._append_iam_test_result("iam_users_present@@" + self.account_id, "iam_user", test_name, "no_issue_found"))
        else:
            result.append(self._append_iam_test_result("iam_users_present@@" + self.account_id, "iam_user", test_name, "issue_found"))

        return result
