import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "lambda_function.py"


def load_lambda_module():
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = MagicMock(side_effect=[MagicMock(name="logs_client"), MagicMock(name="lambda_client")])

    fake_cfnresponse = types.ModuleType("cfnresponse")
    fake_cfnresponse.SUCCESS = "SUCCESS"
    fake_cfnresponse.FAILED = "FAILED"
    fake_cfnresponse.send = MagicMock()

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake_botocore_config.Config = FakeConfig

    module_name = "lambda_manager_lambda_function_test"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)

    with patch.dict(
        sys.modules,
        {
            "boto3": fake_boto3,
            "botocore": fake_botocore,
            "botocore.config": fake_botocore_config,
            "cfnresponse": fake_cfnresponse,
        },
    ):
        spec.loader.exec_module(module)

    return module, fake_cfnresponse


class LambdaManagerCreateLogGroupTests(unittest.TestCase):
    def setUp(self):
        self.module, self.cfnresponse = load_lambda_module()
        self.context = SimpleNamespace(
            invoked_function_arn="arn:aws:lambda:us-east-1:123456789012:function:lambda-manager",
            function_name="lambda-manager",
            aws_request_id="request-id",
        )
        self.destination_arn = "arn:aws:lambda:us-east-1:123456789012:function:destination"

    def invoke_handler(self, event):
        env = {
            "REGEX_PATTERN": "/aws/lambda/.*",
            "DESTINATION_TYPE": "lambda",
            "DESTINATION_ARN": self.destination_arn,
            "SCAN_OLD_LOGGROUPS": "false",
            "DISABLE_ADD_PERMISSION": "false",
            "ADD_PERMISSIONS_TO_ALL_LOG_GROUPS": "false",
            "LOG_GROUP_PERMISSION_PREFIX": "",
        }

        with patch.dict(os.environ, env, clear=False):
            self.module.lambda_handler(event, self.context)

    def test_failed_create_log_group_event_is_ignored(self):
        event = {
            "detail": {
                "requestParameters": {"logGroupName": "/aws/lambda/example"},
                "errorCode": "ResourceAlreadyExistsException",
                "errorMessage": "The specified log group already exists",
            }
        }

        with patch.object(self.module, "add_permission_to_lambda") as add_permission, patch.object(
            self.module, "add_subscription"
        ) as add_subscription:
            self.invoke_handler(event)

        add_permission.assert_not_called()
        add_subscription.assert_not_called()
        self.module.cloudwatch_logs.describe_subscription_filters.assert_not_called()

    def test_existing_destination_subscription_is_not_duplicated(self):
        event = {"detail": {"requestParameters": {"logGroupName": "/aws/lambda/example"}}}
        self.module.cloudwatch_logs.describe_subscription_filters.return_value = {
            "subscriptionFilters": [{"destinationArn": self.destination_arn}]
        }

        with patch.object(self.module, "add_permission_to_lambda") as add_permission, patch.object(
            self.module, "add_subscription"
        ) as add_subscription:
            self.invoke_handler(event)

        self.module.cloudwatch_logs.describe_subscription_filters.assert_called_once_with(
            logGroupName="/aws/lambda/example"
        )
        add_permission.assert_not_called()
        add_subscription.assert_not_called()

    def test_event_without_log_group_class_still_gets_subscribed(self):
        event = {"detail": {"requestParameters": {"logGroupName": "/aws/lambda/example"}}}
        self.module.cloudwatch_logs.describe_subscription_filters.return_value = {"subscriptionFilters": []}

        with patch.object(self.module, "add_permission_to_lambda") as add_permission, patch.object(
            self.module, "add_subscription", return_value=self.cfnresponse.SUCCESS
        ) as add_subscription:
            self.invoke_handler(event)

        add_permission.assert_called_once_with(
            self.destination_arn,
            "/aws/lambda/example",
            "us-east-1",
            "123456789012",
        )
        add_subscription.assert_called_once()

    def test_non_standard_log_group_class_is_ignored(self):
        for log_group_class in ("INFREQUENT_ACCESS", "DELIVERY"):
            event = {
                "detail": {
                    "requestParameters": {
                        "logGroupName": "/aws/lambda/example",
                        "logGroupClass": log_group_class,
                    }
                }
            }

            with self.subTest(log_group_class=log_group_class):
                with patch.object(self.module, "add_permission_to_lambda") as add_permission, patch.object(
                    self.module, "add_subscription"
                ) as add_subscription:
                    self.invoke_handler(event)

                add_permission.assert_not_called()
                add_subscription.assert_not_called()

if __name__ == "__main__":
    unittest.main()
