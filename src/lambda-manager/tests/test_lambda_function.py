import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lambda_manager_test_support import (
    base_environment,
    cloudformation_event,
    load_lambda_module,
)


class LambdaManagerDispatchTests(unittest.TestCase):
    def setUp(self):
        self.module, self.cfnresponse, self.clients = load_lambda_module()
        self.context = SimpleNamespace(
            invoked_function_arn=(
                "arn:aws:lambda:us-east-1:123456789012:function:lambda-manager"
            ),
            function_name="lambda-manager",
            aws_request_id="request-id",
        )
        self.result = self.module.ReconciliationResult(
            scanned=2, inspected=1, created=1
        )

    def invoke_direct(self, event, **environment):
        with patch.dict(os.environ, base_environment(**environment), clear=True):
            return self.module.lambda_handler(event, self.context)

    def test_direct_reconcile_dispatches_without_a_cloudformation_response(self):
        with patch.object(
            self.module, "reconcile_subscriptions", return_value=self.result
        ) as reconcile:
            response = self.invoke_direct({"RequestType": "reConCiLe"})

        reconcile.assert_called_once()
        self.assertEqual("Reconcile", response["requestType"])
        self.assertEqual("SUCCESS", response["status"])
        self.cfnresponse.send.assert_not_called()

    def test_direct_cleanup_dispatches_without_a_cloudformation_response(self):
        with (
            patch.object(
                self.module, "cleanup_managed_subscriptions", return_value=self.result
            ) as cleanup,
            patch.object(self.module, "reconcile_subscriptions") as reconcile,
        ):
            with patch.dict(os.environ, {}, clear=True):
                response = self.module.lambda_handler(
                    {"RequestType": "cLeAnUp"}, self.context
                )

        cleanup.assert_called_once()
        reconcile.assert_not_called()
        self.assertEqual("Cleanup", response["requestType"])
        self.assertEqual("SUCCESS", response["status"])
        self.cfnresponse.send.assert_not_called()

        with patch.object(
            self.module,
            "cleanup_managed_subscriptions",
            side_effect=RuntimeError("cleanup blocked"),
        ):
            with self.assertRaisesRegex(RuntimeError, "cleanup blocked"):
                self.invoke_direct({"RequestType": "Cleanup"})

    def test_terraform_lifecycle_reconciles_then_cleans_up_on_delete(self):
        with (
            patch.object(
                self.module, "reconcile_subscriptions", return_value=self.result
            ) as reconcile,
            patch.object(
                self.module, "cleanup_managed_subscriptions", return_value=self.result
            ) as cleanup,
        ):
            for action in ("create", "update"):
                response = self.invoke_direct(
                    {"RequestType": "Reconcile", "tf": {"action": action}}
                )
                self.assertEqual("Reconcile", response["requestType"])

            with patch.dict(os.environ, {}, clear=True):
                response = self.module.lambda_handler(
                    {"RequestType": "Reconcile", "tf": {"action": "delete"}},
                    self.context,
                )

        self.assertEqual(2, reconcile.call_count)
        cleanup.assert_called_once()
        self.assertEqual("Cleanup", response["requestType"])

    def test_direct_overrides_and_configuration_are_validated(self):
        for invalid in ("true", 1, None):
            for field in ("Repair", "AdoptLegacyFilters"):
                with self.subTest(field=field, invalid=invalid):
                    with self.assertRaisesRegex(ValueError, "must be a boolean"):
                        self.invoke_direct({"RequestType": "Reconcile", field: invalid})

        with patch.object(
            self.module, "reconcile_subscriptions", return_value=self.result
        ) as reconcile:
            self.invoke_direct(
                {
                    "RequestType": "Reconcile",
                    "Repair": True,
                    "AdoptLegacyFilters": False,
                },
                ADOPT_LEGACY_FILTERS="true",
            )

        config = reconcile.call_args.args[0]
        self.assertFalse(config.adopt_legacy_filters)
        self.assertTrue(reconcile.call_args.kwargs["repair"])

        with patch.object(
            self.module, "reconcile_subscriptions", return_value=self.result
        ) as reconcile:
            self.invoke_direct(
                {"RequestType": "Reconcile"}, ADOPT_LEGACY_FILTERS="true"
            )
        self.assertTrue(reconcile.call_args.args[0].adopt_legacy_filters)

        with patch.object(self.module, "reconcile_subscriptions") as reconcile:
            for pattern, message in (
                ("[", "Invalid RegexPattern"),
                (",,", "must include at least one expression"),
            ):
                with self.subTest(pattern=pattern):
                    with self.assertRaisesRegex(ValueError, message):
                        self.invoke_direct(
                            {"RequestType": "Reconcile"}, REGEX_PATTERN=pattern
                        )
        reconcile.assert_not_called()

    def test_cloudformation_sparse_properties_fall_back_to_environment(self):
        sparse = cloudformation_event(
            "Update", ResourceProperties={"ServiceToken": "manager-arn"}
        )
        with patch.dict(
            os.environ,
            base_environment(LOGS_FILTER="from-environment"),
            clear=True,
        ):
            config = self.module.load_config(sparse, self.context)

        self.assertEqual("from-environment", config.logs_filter)

    def test_cloudformation_create_and_update_reconcile_and_respond(self):
        with patch.object(
            self.module, "reconcile_subscriptions", return_value=self.result
        ) as reconcile:
            create_response = self.module.lambda_handler(
                cloudformation_event("Create"),
                self.context,
            )
            update_event = cloudformation_event("Update")
            update_response = self.module.lambda_handler(update_event, self.context)

        self.assertEqual("SUCCESS", create_response["status"])
        self.assertEqual("SUCCESS", update_response["status"])
        self.assertEqual(2, reconcile.call_count)
        self.assertEqual(2, self.cfnresponse.send.call_count)

    def test_cloudformation_delete_uses_exact_cleanup_and_never_reconciles(self):
        with (
            patch.object(
                self.module, "cleanup_managed_subscriptions", return_value=self.result
            ) as cleanup,
            patch.object(self.module, "reconcile_subscriptions") as reconcile,
        ):
            response = self.module.lambda_handler(
                cloudformation_event("Delete", ResourceProperties={}), self.context
            )

        cleanup.assert_called_once()
        reconcile.assert_not_called()
        self.assertEqual("SUCCESS", response["status"])

    def test_cloudformation_and_direct_failures_follow_their_event_contracts(self):
        with patch.object(
            self.module, "reconcile_subscriptions", side_effect=RuntimeError("blocked")
        ):
            response = self.module.lambda_handler(
                cloudformation_event("Create"), self.context
            )

        self.assertEqual({"status": "FAILED", "requestType": "Create"}, response)
        self.assertEqual(
            self.cfnresponse.FAILED, self.cfnresponse.send.call_args.args[2]
        )
        self.assertEqual("blocked", self.cfnresponse.send.call_args.kwargs["reason"])

        self.cfnresponse.send.reset_mock()
        with patch.object(
            self.module, "reconcile_subscriptions", side_effect=RuntimeError("blocked")
        ):
            with self.assertRaisesRegex(RuntimeError, "blocked"):
                self.invoke_direct({"RequestType": "Reconcile"})
        self.cfnresponse.send.assert_not_called()

    def test_create_log_group_uses_single_group_reconciliation(self):
        event = {
            "detail": {
                "eventName": "CreateLogGroup",
                "requestParameters": {"logGroupName": "/aws/lambda/example"},
            },
        }
        with patch.object(
            self.module, "reconcile_log_group", return_value=self.result
        ) as reconcile:
            response = self.invoke_direct(event, ADOPT_LEGACY_FILTERS="false")

        reconcile.assert_called_once()
        self.assertEqual("CreateLogGroup", response["requestType"])

    def test_failed_and_non_standard_create_events_are_ignored(self):
        failed = {
            "detail": {
                "eventName": "CreateLogGroup",
                "requestParameters": {"logGroupName": "/aws/lambda/example"},
                "errorCode": "ResourceAlreadyExistsException",
            }
        }
        nonstandard = {
            "detail": {
                "eventName": "CreateLogGroup",
                "requestParameters": {
                    "logGroupName": "/aws/lambda/example",
                    "logGroupClass": "INFREQUENT_ACCESS",
                },
            }
        }
        with patch.object(self.module, "reconcile_log_group") as reconcile:
            self.assertIsNone(self.invoke_direct(failed))
            self.assertIsNone(self.invoke_direct(nonstandard))
        reconcile.assert_not_called()

    def test_unknown_direct_events_are_rejected(self):
        for event in (
            {"RequestType": "Create"},
            {},
            {"detail": {}},
            {"detail": {"requestParameters": {"logGroupName": "/aws/lambda/x"}}},
        ):
            with self.subTest(event=event):
                with self.assertRaises(ValueError):
                    self.invoke_direct(event)


if __name__ == "__main__":
    unittest.main()
