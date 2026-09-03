import os
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from lambda_manager_test_support import base_environment, load_lambda_module


class AwsError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class LambdaManagerReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.module, _, self.clients = load_lambda_module()
        self.logs = self.clients["logs"]
        self.tagging = self.clients["resourcegroupstaggingapi"]
        self.lambda_client = self.clients["lambda"]
        self.context = SimpleNamespace(
            invoked_function_arn=(
                "arn:aws:lambda:us-east-1:123456789012:function:lambda-manager"
            )
        )
        self.tagging.get_resources.return_value = {"ResourceTagMappingList": []}
        self.logs.describe_log_groups.return_value = {"logGroups": []}

    def config(self, event=None, **environment):
        with patch.dict(os.environ, base_environment(**environment), clear=True):
            return self.module.load_config(event or {}, self.context)

    def arn(self, name):
        return f"arn:aws:logs:us-east-1:123456789012:log-group:{name}"

    def group(self, name):
        return {"logGroupName": name, "arn": f"{self.arn(name)}:*"}

    def managed_filter(self, config, **overrides):
        result = {
            "filterName": config.managed_filter_name,
            "destinationArn": config.destination_arn,
            "filterPattern": config.logs_filter,
        }
        result.update(overrides)
        return result

    def test_ownership_is_stable_across_qualifiers_and_unique_per_function(self):
        base = self.config()
        self.assertTrue(
            base.managed_filter_name.startswith("Coralogix_Lambda_Manager_")
        )
        self.assertTrue(base.managed_tag_key.startswith("coralogix:lambda-manager:"))
        self.assertLessEqual(len(base.managed_tag_key), 128)

        self.assertEqual(
            base.managed_tag_value,
            self.config(REGEX_PATTERN=r"^/different/scope/.*").managed_tag_value,
        )
        self.assertNotEqual(
            base.managed_tag_value,
            self.config(LOGS_FILTER="ERROR").managed_tag_value,
        )
        self.assertEqual(
            base.managed_tag_value,
            self.config(ADOPT_LEGACY_FILTERS="true").managed_tag_value,
        )
        for permission_configuration in (
            {"DISABLE_ADD_PERMISSION": "true"},
            {"ADD_PERMISSIONS_TO_ALL_LOG_GROUPS": "true"},
            {"LOG_GROUP_PERMISSION_PREFIX": "/aws/lambda/team"},
        ):
            self.assertNotEqual(
                base.managed_tag_value,
                self.config(**permission_configuration).managed_tag_value,
            )
        self.assertNotEqual(
            base.managed_tag_value,
            self.config(
                DESTINATION_ARN=("arn:aws:lambda:us-east-1:123456789012:function:other")
            ).managed_tag_value,
        )

        for qualifier in (":live", ":42"):
            self.context.invoked_function_arn = base.manager_lambda_arn + qualifier
            qualified = self.config()
            self.assertEqual(base.managed_filter_name, qualified.managed_filter_name)
            self.assertEqual(base.manager_lambda_arn, qualified.manager_lambda_arn)
            self.assertEqual(base.managed_tag_value, qualified.managed_tag_value)

        self.context.invoked_function_arn = (
            "arn:aws:lambda:eu-west-1:999999999999:function:lambda-manager"
        )
        self.assertNotEqual(base.managed_filter_name, self.config().managed_filter_name)

    def test_paginated_discovery_inspects_only_matching_or_indexed_groups(self):
        config = self.config()
        matching = "/aws/lambda/matching"
        current = "/aws/lambda/current"
        indexed = "/old/indexed"
        ignored = "/other/ignored"
        self.tagging.get_resources.side_effect = [
            {
                "ResourceTagMappingList": [
                    {
                        "ResourceARN": self.arn(indexed),
                        "Tags": [{"Key": config.managed_tag_key, "Value": "stale-arn"}],
                    },
                    {
                        "ResourceARN": self.arn(current),
                        "Tags": [
                            {
                                "Key": config.managed_tag_key,
                                "Value": config.managed_tag_value,
                            }
                        ],
                    },
                ],
                "PaginationToken": "next",
            },
            {"ResourceTagMappingList": [], "PaginationToken": ""},
        ]
        self.logs.describe_log_groups.side_effect = [
            {
                "logGroups": [
                    self.group(matching),
                    self.group(current),
                    self.group(ignored),
                ],
                "nextToken": "groups-next",
            },
            {"logGroups": [self.group(indexed)]},
        ]
        workers_started = threading.Barrier(2)

        def describe_subscriptions(**kwargs):
            workers_started.wait(timeout=1)
            return {
                "subscriptionFilters": [self.managed_filter(config)]
                if kwargs["logGroupName"] == indexed
                else []
            }

        self.logs.describe_subscription_filters.side_effect = describe_subscriptions

        result = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(4, result.scanned)
        self.assertEqual(2, result.indexed)
        self.assertEqual(2, result.inspected)
        self.assertEqual(1, result.created)
        self.assertEqual(1, result.deleted)
        self.assertEqual(2, result.unchanged)
        self.assertEqual(2, self.tagging.get_resources.call_count)
        self.assertEqual(
            [{"Key": config.managed_tag_key}],
            self.tagging.get_resources.call_args_list[0].kwargs["TagFilters"],
        )
        self.assertEqual(
            "next",
            self.tagging.get_resources.call_args_list[1].kwargs["PaginationToken"],
        )
        self.assertEqual(2, self.logs.describe_log_groups.call_count)
        self.assertEqual(
            "STANDARD",
            self.logs.describe_log_groups.call_args_list[0].kwargs["logGroupClass"],
        )
        self.assertEqual(
            "groups-next",
            self.logs.describe_log_groups.call_args_list[1].kwargs["nextToken"],
        )
        inspected_names = {
            item.kwargs["logGroupName"]
            for item in self.logs.describe_subscription_filters.call_args_list
        }
        self.assertEqual({matching, indexed}, inspected_names)

    def test_permission_is_ensured_only_for_invalidated_hash_or_repair(self):
        config = self.config()
        previous = self.config(DISABLE_ADD_PERMISSION="true")
        name = "/aws/lambda/existing"
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [self.managed_filter(config)]
        }

        def indexed_with(value):
            return {
                "ResourceTagMappingList": [
                    {
                        "ResourceARN": self.arn(name),
                        "Tags": [{"Key": config.managed_tag_key, "Value": value}],
                    }
                ]
            }

        self.tagging.get_resources.return_value = indexed_with(
            previous.managed_tag_value
        )
        invalidated = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, invalidated.inspected)
        self.lambda_client.add_permission.assert_called_once()
        self.logs.put_subscription_filter.assert_not_called()
        self.logs.tag_resource.assert_called_once_with(
            resourceArn=self.arn(name),
            tags={config.managed_tag_key: config.managed_tag_value},
        )

        self.lambda_client.add_permission.reset_mock()
        self.logs.describe_subscription_filters.reset_mock()
        self.logs.tag_resource.reset_mock()
        self.tagging.get_resources.return_value = indexed_with(config.managed_tag_value)

        current = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(0, current.inspected)
        self.lambda_client.add_permission.assert_not_called()
        self.logs.describe_subscription_filters.assert_not_called()

        repaired = self.module.reconcile_subscriptions(
            config, self.context, repair=True
        )

        self.assertEqual(1, repaired.inspected)
        self.lambda_client.add_permission.assert_called_once()
        self.logs.describe_subscription_filters.assert_called_once()
        self.logs.tag_resource.assert_not_called()

    def test_shared_permission_scope_is_added_once_per_reconciliation(self):
        config = self.config(LOG_GROUP_PERMISSION_PREFIX="/aws/lambda/team/")
        names = ("/aws/lambda/team/one", "/aws/lambda/team/two")
        self.tagging.get_resources.return_value = {"ResourceTagMappingList": []}
        self.logs.describe_log_groups.return_value = {
            "logGroups": [self.group(name) for name in names]
        }
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": []
        }
        self.lambda_client.add_permission.side_effect = AwsError(
            "ResourceConflictException"
        )

        result = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(2, result.created)
        self.assertEqual(1, self.lambda_client.add_permission.call_count)
        self.assertTrue(
            self.lambda_client.add_permission.call_args.kwargs["SourceArn"].endswith(
                "log-group:/aws/lambda/team/*:*"
            )
        )

    def test_owned_filter_drift_is_updated_and_stale_tag_value_repaired(self):
        config = self.config(LOGS_FILTER="ERROR")
        name = "/aws/lambda/drifted"
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(name),
                    "Tags": [{"Key": config.managed_tag_key, "Value": "old-arn"}],
                }
            ]
        }
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [
                self.managed_filter(
                    config,
                    filterPattern="old-filter",
                    destinationArn="arn:aws:lambda:us-east-1:123456789012:function:old",
                )
            ]
        }

        result = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, result.updated)
        self.lambda_client.add_permission.assert_called_once()
        self.logs.put_subscription_filter.assert_called_once_with(
            destinationArn=config.destination_arn,
            filterName=config.managed_filter_name,
            filterPattern="ERROR",
            logGroupName=name,
        )
        self.logs.tag_resource.assert_called_once_with(
            resourceArn=self.arn(name),
            tags={config.managed_tag_key: config.managed_tag_value},
        )

    def test_owned_filter_destination_update_blocks_same_destination_conflict(self):
        config = self.config()
        name = "/aws/lambda/conflicting-update"
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(name),
                    "Tags": [{"Key": config.managed_tag_key, "Value": "stale"}],
                }
            ]
        }
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [
                self.managed_filter(
                    config,
                    destinationArn=(
                        "arn:aws:lambda:us-east-1:123456789012:function:old"
                    ),
                ),
                {
                    "filterName": "manual-filter",
                    "destinationArn": config.destination_arn,
                },
            ]
        }

        with self.assertRaisesRegex(RuntimeError, "manual-filter"):
            self.module.reconcile_subscriptions(config, self.context)

        self.logs.put_subscription_filter.assert_not_called()
        self.logs.delete_subscription_filter.assert_not_called()
        self.logs.tag_resource.assert_not_called()
        self.logs.untag_resource.assert_called_once_with(
            resourceArn=self.arn(name), tagKeys=[config.managed_tag_key]
        )
        self.lambda_client.add_permission.assert_not_called()

    def test_only_indexed_nonmatching_filter_is_deleted_before_tag_removal(self):
        config = self.config()
        indexed_name = "/old/indexed"
        untagged_name = "/old/untagged"
        self.logs.describe_log_groups.return_value = {
            "logGroups": [self.group(indexed_name), self.group(untagged_name)]
        }
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(indexed_name),
                    "Tags": [
                        {
                            "Key": config.managed_tag_key,
                            "Value": config.managed_tag_value,
                        }
                    ],
                }
            ]
        }
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [self.managed_filter(config)]
        }

        result = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, result.inspected)
        self.assertEqual(1, result.deleted)
        self.logs.describe_subscription_filters.assert_called_once_with(
            logGroupName=indexed_name
        )
        self.assertEqual(
            ["delete_subscription_filter", "untag_resource"],
            [
                method[0]
                for method in self.logs.method_calls
                if method[0] in ("delete_subscription_filter", "untag_resource")
            ],
        )

    def test_repair_finds_missing_tag_but_never_adopts_nonmatching_legacy(self):
        config = self.config(ADOPT_LEGACY_FILTERS="true")
        managed_name = "/aws/lambda/missing-tag"
        current_name = "/aws/lambda/current-tag"
        legacy_name = "/old/legacy"
        legacy_filter = {
            "filterName": "Coralogix_Filter_12345678-1234-4234-9234-123456789abc",
            "destinationArn": config.destination_arn,
            "filterPattern": "",
        }
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(current_name),
                    "Tags": [
                        {
                            "Key": config.managed_tag_key,
                            "Value": config.managed_tag_value,
                        }
                    ],
                }
            ]
        }
        self.logs.describe_log_groups.return_value = {
            "logGroups": [
                self.group(managed_name),
                self.group(current_name),
                self.group(legacy_name),
            ]
        }
        self.logs.describe_subscription_filters.side_effect = lambda **kwargs: {
            "subscriptionFilters": [self.managed_filter(config)]
            if kwargs["logGroupName"] in (managed_name, current_name)
            else [legacy_filter]
        }

        result = self.module.reconcile_subscriptions(config, self.context, repair=True)

        self.assertEqual(3, result.inspected)
        self.assertEqual(0, result.legacy_adopted)
        self.logs.tag_resource.assert_called_once_with(
            resourceArn=self.arn(managed_name),
            tags={config.managed_tag_key: config.managed_tag_value},
        )
        self.logs.delete_subscription_filter.assert_not_called()

    def test_failed_repair_invalidates_current_hash_for_normal_retry(self):
        config = self.config(LOGS_FILTER="ERROR")
        name = "/aws/lambda/repair-retry"
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(name),
                    "Tags": [
                        {
                            "Key": config.managed_tag_key,
                            "Value": config.managed_tag_value,
                        }
                    ],
                }
            ]
        }
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [
                self.managed_filter(config, filterPattern="old-filter")
            ]
        }
        self.logs.put_subscription_filter.side_effect = [
            AwsError("ServiceUnavailableException"),
            None,
        ]

        with self.assertRaises(AwsError):
            self.module.reconcile_subscriptions(config, self.context, repair=True)
        self.logs.untag_resource.assert_called_once_with(
            resourceArn=self.arn(name), tagKeys=[config.managed_tag_key]
        )
        self.logs.tag_resource.assert_not_called()

        self.tagging.get_resources.return_value = {"ResourceTagMappingList": []}
        result = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, result.updated)
        self.assertEqual(2, self.logs.put_subscription_filter.call_count)
        self.logs.tag_resource.assert_called_once_with(
            resourceArn=self.arn(name),
            tags={config.managed_tag_key: config.managed_tag_value},
        )

    def test_legacy_adoption_requires_opt_in_and_renames_then_tags(self):
        legacy_name = "Coralogix_Filter_12345678-1234-4234-9234-123456789abc"
        name = "/aws/lambda/legacy"
        disabled = self.config(ADOPT_LEGACY_FILTERS="false")
        enabled = self.config(ADOPT_LEGACY_FILTERS="true")
        legacy = {
            "filterName": legacy_name,
            "destinationArn": enabled.destination_arn,
            "filterPattern": "",
        }
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [legacy]
        }

        skipped = self.module.reconcile_subscriptions(disabled, self.context)
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(name),
                    "Tags": [
                        {
                            "Key": enabled.managed_tag_key,
                            "Value": enabled.managed_tag_value,
                        }
                    ],
                }
            ]
        }
        adopted = self.module.reconcile_subscriptions(enabled, self.context)

        self.assertEqual(1, skipped.legacy_skipped)
        self.assertEqual(1, adopted.legacy_adopted)
        self.logs.put_subscription_filter.assert_called_once()
        self.logs.delete_subscription_filter.assert_called_once_with(
            logGroupName=name, filterName=legacy_name
        )
        self.logs.tag_resource.assert_called_once()

    def test_limit_fallback_deletes_only_adopted_legacy_filter(self):
        config = self.config(ADOPT_LEGACY_FILTERS="true", DISABLE_ADD_PERMISSION="true")
        name = "/aws/lambda/legacy"
        legacy_name = "Coralogix_Filter_12345678-1234-4234-9234-123456789abc"
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [
                {"filterName": legacy_name, "destinationArn": config.destination_arn},
                {
                    "filterName": "unrelated",
                    "destinationArn": "arn:aws:lambda:us-east-1:123456789012:function:other",
                },
            ]
        }
        self.logs.put_subscription_filter.side_effect = [
            AwsError("LimitExceededException"),
            None,
        ]

        result = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, result.legacy_adopted)
        self.assertEqual(2, self.logs.put_subscription_filter.call_count)
        self.logs.delete_subscription_filter.assert_called_once_with(
            logGroupName=name, filterName=legacy_name
        )

    def test_tag_failure_after_create_is_repaired_without_second_put(self):
        config = self.config(DISABLE_ADD_PERMISSION="true")
        name = "/aws/lambda/tag-retry"
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.side_effect = [
            {"subscriptionFilters": []},
            {"subscriptionFilters": [self.managed_filter(config)]},
        ]
        self.logs.tag_resource.side_effect = [AwsError("AccessDeniedException"), None]

        with self.assertRaises(AwsError):
            self.module.reconcile_subscriptions(config, self.context)
        rerun = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, rerun.unchanged)
        self.assertEqual(1, self.logs.put_subscription_filter.call_count)
        self.assertEqual(2, self.logs.tag_resource.call_count)
        put_index = next(
            index
            for index, method in enumerate(self.logs.method_calls)
            if method[0] == "put_subscription_filter"
        )
        tag_index = next(
            index
            for index, method in enumerate(self.logs.method_calls)
            if method[0] == "tag_resource"
        )
        self.assertLess(put_index, tag_index)

    def test_delete_failure_after_legacy_put_finishes_on_rerun(self):
        config = self.config(ADOPT_LEGACY_FILTERS="true", DISABLE_ADD_PERMISSION="true")
        name = "/aws/lambda/delete-retry"
        legacy_name = "Coralogix_Filter_12345678-1234-4234-9234-123456789abc"
        legacy = {"filterName": legacy_name, "destinationArn": config.destination_arn}
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.side_effect = [
            {"subscriptionFilters": [legacy]},
            {"subscriptionFilters": [self.managed_filter(config), legacy]},
        ]
        self.logs.delete_subscription_filter.side_effect = [
            AwsError("ServiceUnavailableException"),
            None,
        ]

        with self.assertRaises(AwsError):
            self.module.reconcile_subscriptions(config, self.context)
        rerun = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, rerun.legacy_adopted)
        self.assertEqual(1, self.logs.put_subscription_filter.call_count)
        self.assertEqual(2, self.logs.delete_subscription_filter.call_count)

    def test_failed_quota_fallback_put_is_restored_on_rerun(self):
        config = self.config(ADOPT_LEGACY_FILTERS="true", DISABLE_ADD_PERMISSION="true")
        name = "/aws/lambda/fallback-retry"
        legacy_name = "Coralogix_Filter_12345678-1234-4234-9234-123456789abc"
        self.logs.describe_log_groups.return_value = {"logGroups": [self.group(name)]}
        self.logs.describe_subscription_filters.side_effect = [
            {
                "subscriptionFilters": [
                    {
                        "filterName": legacy_name,
                        "destinationArn": config.destination_arn,
                    }
                ]
            },
            {"subscriptionFilters": []},
        ]
        self.logs.put_subscription_filter.side_effect = [
            AwsError("LimitExceededException"),
            AwsError("ServiceUnavailableException"),
            None,
        ]

        with self.assertRaises(AwsError):
            self.module.reconcile_subscriptions(config, self.context)
        rerun = self.module.reconcile_subscriptions(config, self.context)

        self.assertEqual(1, rerun.created)
        self.assertEqual(3, self.logs.put_subscription_filter.call_count)
        self.logs.delete_subscription_filter.assert_called_once_with(
            logGroupName=name, filterName=legacy_name
        )

    def test_blocked_reconciliation_never_deletes_unowned_filters(self):
        config = self.config(DISABLE_ADD_PERMISSION="true")
        scenarios = (
            (config.destination_arn, None, "not adoptable"),
            (
                "arn:aws:lambda:us-east-1:123456789012:function:other",
                AwsError("LimitExceededException"),
                "subscription quota is full",
            ),
        )

        for destination_arn, put_error, message in scenarios:
            with self.subTest(message=message):
                self.logs.reset_mock()
                self.logs.describe_log_groups.return_value = {
                    "logGroups": [self.group("/aws/lambda/blocked")]
                }
                self.logs.describe_subscription_filters.return_value = {
                    "subscriptionFilters": [
                        {
                            "filterName": "manual-filter",
                            "destinationArn": destination_arn,
                        }
                    ]
                }
                self.logs.put_subscription_filter.side_effect = put_error

                with self.assertRaisesRegex(RuntimeError, message):
                    self.module.reconcile_subscriptions(config, self.context)
                self.logs.delete_subscription_filter.assert_not_called()

    def test_firehose_includes_role_and_lambda_omits_it(self):
        firehose = self.config(
            DESTINATION_ARN=(
                "arn:aws:firehose:us-east-1:123456789012:deliverystream/destination"
            ),
            DESTINATION_ROLE="arn:aws:iam::123456789012:role/logs-firehose",
        )
        self.logs.describe_log_groups.return_value = {
            "logGroups": [self.group("/aws/lambda/firehose")]
        }
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": []
        }
        self.module.reconcile_subscriptions(firehose, self.context)
        self.assertEqual(
            firehose.destination_role,
            self.logs.put_subscription_filter.call_args.kwargs["roleArn"],
        )

        self.logs.reset_mock()
        self.tagging.reset_mock()
        self.tagging.get_resources.return_value = {"ResourceTagMappingList": []}
        lambda_config = self.config(DESTINATION_ROLE="ignored-for-lambda")
        self.logs.describe_log_groups.return_value = {
            "logGroups": [self.group("/aws/lambda/lambda")]
        }
        self.logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": []
        }
        self.module.reconcile_subscriptions(lambda_config, self.context)
        self.assertNotIn("roleArn", self.logs.put_subscription_filter.call_args.kwargs)

    def test_cleanup_directly_deletes_only_indexed_deterministic_filters(self):
        config = self.config()
        owned_name = "/aws/lambda/owned"
        stale_name = "/aws/lambda/stale"
        self.tagging.get_resources.return_value = {
            "ResourceTagMappingList": [
                {
                    "ResourceARN": self.arn(owned_name),
                    "Tags": [{"Key": config.managed_tag_key, "Value": "stale"}],
                },
                {
                    "ResourceARN": self.arn(stale_name),
                    "Tags": [{"Key": config.managed_tag_key, "Value": "stale"}],
                },
            ]
        }

        def delete_subscription(**kwargs):
            if kwargs["logGroupName"] == stale_name:
                raise AwsError("ResourceNotFoundException")

        self.logs.delete_subscription_filter.side_effect = delete_subscription

        result = self.module.cleanup_managed_subscriptions(config)

        self.assertEqual(2, result.scanned)
        self.assertEqual(2, result.indexed)
        self.assertEqual(0, result.inspected)
        self.assertEqual(1, result.deleted)
        self.assertEqual(1, result.unchanged)
        self.assertCountEqual(
            [
                call(
                    logGroupName=owned_name,
                    filterName=config.managed_filter_name,
                ),
                call(
                    logGroupName=stale_name,
                    filterName=config.managed_filter_name,
                ),
            ],
            self.logs.delete_subscription_filter.call_args_list,
        )
        self.assertCountEqual(
            [
                call(
                    resourceArn=self.arn(owned_name),
                    tagKeys=[config.managed_tag_key],
                ),
                call(
                    resourceArn=self.arn(stale_name),
                    tagKeys=[config.managed_tag_key],
                ),
            ],
            self.logs.untag_resource.call_args_list,
        )
        self.logs.describe_log_groups.assert_not_called()
        self.logs.describe_subscription_filters.assert_not_called()

    def test_lambda_permissions_are_bounded_partition_aware_and_scope_correctly(self):
        destination = "arn:aws-us-gov:lambda:us-gov-west-1:123456789012:function:dest"
        long_name = "/aws/lambda/" + ("x" * 500)
        self.module.add_permission_to_lambda(
            destination, long_name, "us-gov-west-1", "123456789012"
        )
        first = self.lambda_client.add_permission.call_args.kwargs
        self.assertLessEqual(len(first["StatementId"]), 100)
        self.assertTrue(first["SourceArn"].startswith("arn:aws-us-gov:logs:"))

        self.module.add_permission_to_lambda(
            destination, "/aws/a.b", "us-gov-west-1", "123456789012"
        )
        dotted = self.lambda_client.add_permission.call_args.kwargs["StatementId"]
        self.module.add_permission_to_lambda(
            destination, "/aws/a/b", "us-gov-west-1", "123456789012"
        )
        slashed = self.lambda_client.add_permission.call_args.kwargs["StatementId"]
        self.assertNotEqual(dotted, slashed)

        self.lambda_client.reset_mock()
        prefix_config = self.config(LOG_GROUP_PERMISSION_PREFIX="/aws/lambda/")
        self.module._ensure_destination_permission("/aws/lambda/example", prefix_config)
        self.assertTrue(
            self.lambda_client.add_permission.call_args.kwargs["SourceArn"].endswith(
                "log-group:/aws/lambda/*:*"
            )
        )

        self.lambda_client.reset_mock()
        wildcard_config = self.config(ADD_PERMISSIONS_TO_ALL_LOG_GROUPS="true")
        self.module._ensure_destination_permission(
            "/aws/lambda/example", wildcard_config
        )
        self.assertTrue(
            self.lambda_client.add_permission.call_args.kwargs["SourceArn"].endswith(
                "log-group:*:*"
            )
        )


if __name__ == "__main__":
    unittest.main()
