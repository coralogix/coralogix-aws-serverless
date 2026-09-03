import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "lambda_function.py"


def load_lambda_module():
    clients = {
        "logs": MagicMock(name="logs_client"),
        "lambda": MagicMock(name="lambda_client"),
        "resourcegroupstaggingapi": MagicMock(name="tagging_client"),
    }
    fake_boto3 = types.ModuleType("boto3")
    setattr(
        fake_boto3,
        "client",
        MagicMock(side_effect=lambda service, **kwargs: clients[service]),
    )

    fake_cfnresponse = types.ModuleType("cfnresponse")
    setattr(fake_cfnresponse, "SUCCESS", "SUCCESS")
    setattr(fake_cfnresponse, "FAILED", "FAILED")
    setattr(fake_cfnresponse, "send", MagicMock())

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    setattr(fake_botocore_config, "Config", FakeConfig)
    module_name = f"lambda_manager_lambda_function_test_{id(clients)}"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MODULE_PATH}")
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
    module.logger.disabled = True
    setattr(module, "LOGS_API_MIN_INTERVAL_SECONDS", 0)

    return module, fake_cfnresponse, clients


def base_environment(**overrides):
    environment = {
        "REGEX_PATTERN": r"^/aws/lambda/.*",
        "DESTINATION_ARN": "arn:aws:lambda:us-east-1:123456789012:function:destination",
        "DESTINATION_ROLE": "",
        "LOGS_FILTER": "",
        "DISABLE_ADD_PERMISSION": "false",
        "ADD_PERMISSIONS_TO_ALL_LOG_GROUPS": "false",
        "LOG_GROUP_PERMISSION_PREFIX": "",
        "ADOPT_LEGACY_FILTERS": "false",
    }
    environment.update(overrides)
    return environment


def cloudformation_event(request_type="Create", **overrides):
    event = {
        "RequestType": request_type,
        "ResponseURL": "https://example.invalid/response",
        "StackId": "stack-id",
        "LogicalResourceId": "LambdaTrigger",
        "ResourceProperties": {
            "RegexPattern": r"^/aws/lambda/.*",
            "DestinationArn": "arn:aws:lambda:us-east-1:123456789012:function:destination",
            "DestinationRole": "",
            "LogsFilter": "",
            "DisableAddPermission": "false",
            "AddPermissionsToAllLogGroups": "false",
            "LogGroupPermissionPrefix": "",
            "AdoptLegacyFilters": "false",
        },
    }
    event.update(overrides)
    return event
