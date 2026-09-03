import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Pattern,
    Set,
    Tuple,
    TypeVar,
)

import boto3
import cfnresponse
from botocore.config import Config


logger = logging.getLogger("logger")
formatter = logging.Formatter("%(levelname)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

aws_config = Config(
    retries={
        "max_attempts": int(os.environ.get("AWS_API_REQUESTS_LIMIT", 10)),
        "mode": "standard",
    }
)

cloudwatch_logs = boto3.client("logs", config=aws_config)
lambda_client = boto3.client("lambda", config=aws_config)
tagging_client = boto3.client("resourcegroupstaggingapi", config=aws_config)

SUPPORTED_LOG_GROUP_CLASS = "STANDARD"
MANAGED_FILTER_PREFIX = "Coralogix_Lambda_Manager_"
MANAGED_TAG_PREFIX = "coralogix:lambda-manager:"
LEGACY_FILTER_PATTERN = re.compile(
    r"^Coralogix_Filter_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
INDEX_NOT_PRESENT = object()
MAX_RECONCILIATION_WORKERS = 5
LOGS_API_MIN_INTERVAL_SECONDS = 0.2
# Worker count limits concurrent work, not requests per second: fast calls from five
# workers could still exceed CloudWatch Logs' 5 TPS quota. Limit each operation
# independently so requests start 200 ms apart without blocking other API quotas.
_RATE_LIMITED_LOGS_OPERATIONS = (
    "describe_subscription_filters",
    "put_subscription_filter",
    "delete_subscription_filter",
    "tag_resource",
    "untag_resource",
)
_logs_api_rate_locks = {
    operation: threading.Lock() for operation in _RATE_LIMITED_LOGS_OPERATIONS
}
_logs_api_next_call = {operation: 0.0 for operation in _RATE_LIMITED_LOGS_OPERATIONS}
_lambda_permission_lock = threading.Lock()
WorkItem = TypeVar("WorkItem")


@dataclass(frozen=True)
class ManagerIdentity:
    manager_lambda_arn: str
    managed_filter_name: str
    managed_tag_key: str


@dataclass(frozen=True)
class ManagerConfig(ManagerIdentity):
    regex_patterns: Tuple[Pattern[str], ...]
    destination_arn: str
    destination_role: Optional[str]
    logs_filter: str
    disable_add_permission: bool
    add_permissions_to_all_log_groups: bool
    log_group_permission_prefixes: Tuple[str, ...]
    managed_tag_value: str
    adopt_legacy_filters: bool


@dataclass
class ReconciliationResult:
    scanned: int = 0
    indexed: int = 0
    inspected: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    legacy_adopted: int = 0
    legacy_skipped: int = 0
    blocked: int = 0

    def add(self, other: "ReconciliationResult") -> None:
        for field_name in self.__dataclass_fields__:
            setattr(
                self, field_name, getattr(self, field_name) + getattr(other, field_name)
            )


def _is_cloudformation_event(event: Dict[str, Any]) -> bool:
    return all(
        field in event
        for field in ("RequestType", "ResponseURL", "StackId", "LogicalResourceId")
    )


def _parse_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ValueError(f"{name} must be true or false")


def _parse_direct_bool(event: Dict[str, Any], name: str, default: bool) -> bool:
    if name not in event:
        return default
    if not isinstance(event[name], bool):
        raise ValueError(f"{name} must be a boolean")
    return event[name]


def _compile_patterns(
    value: Any, name: str = "RegexPattern"
) -> Tuple[Pattern[str], ...]:
    if value is None:
        raise ValueError(f"{name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a comma-separated string")

    patterns = []
    for raw_pattern in value.split(","):
        pattern = raw_pattern.strip()
        if not pattern:
            continue
        try:
            patterns.append(re.compile(pattern))
        except re.error as error:
            raise ValueError(
                f"Invalid {name} regular expression {pattern!r}: {error}"
            ) from error
    if not patterns:
        raise ValueError(f"{name} must include at least one expression")
    return tuple(patterns)


# Remove an alias or version qualifier so ownership stays stable across invocation methods.
# Example: ...:function:lambda-manager:production -> ...:function:lambda-manager
def unqualified_lambda_arn(invoked_function_arn: str) -> str:
    parts = invoked_function_arn.split(":")
    if len(parts) < 7 or parts[2] != "lambda" or parts[5] != "function" or not parts[6]:
        raise ValueError("context.invoked_function_arn is not a Lambda function ARN")
    return ":".join(parts[:7])


def managed_filter_name(manager_lambda_arn: str) -> str:
    digest = hashlib.sha256(manager_lambda_arn.encode("utf-8")).hexdigest()
    return f"{MANAGED_FILTER_PREFIX}{digest}"


def _manager_identity(context) -> ManagerIdentity:
    manager_lambda_arn = unqualified_lambda_arn(context.invoked_function_arn)
    return ManagerIdentity(
        manager_lambda_arn=manager_lambda_arn,
        managed_filter_name=managed_filter_name(manager_lambda_arn),
        managed_tag_key=_managed_tag_key(manager_lambda_arn),
    )


def _managed_tag_key(manager_lambda_arn: str) -> str:
    digest = hashlib.sha256(manager_lambda_arn.encode("utf-8")).hexdigest()
    return f"{MANAGED_TAG_PREFIX}{digest}"


def _managed_tag_value(
    destination_arn: str,
    destination_role: Optional[str],
    logs_filter: str,
    disable_add_permission: bool,
    add_permissions_to_all_log_groups: bool,
    log_group_permission_prefixes: Tuple[str, ...],
) -> str:
    desired_configuration = json.dumps(
        {
            "destinationArn": destination_arn,
            "filterPattern": logs_filter,
            "roleArn": destination_role,
            "disableAddPermission": disable_add_permission,
            "addPermissionsToAllLogGroups": add_permissions_to_all_log_groups,
            "logGroupPermissionPrefixes": log_group_permission_prefixes,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(desired_configuration.encode("utf-8")).hexdigest()
    return digest


def _config_value(
    source: Mapping[str, Any], property_name: str, environment_name: str, default=None
):
    if property_name in source:
        return source[property_name]
    return os.environ.get(environment_name, default)


def load_config(event: Dict[str, Any], context) -> ManagerConfig:
    is_cloudformation = _is_cloudformation_event(event)
    source = event.get("ResourceProperties", {}) if is_cloudformation else os.environ

    regex_patterns = _compile_patterns(
        _config_value(source, "RegexPattern", "REGEX_PATTERN"), "RegexPattern"
    )
    destination_arn = _config_value(source, "DestinationArn", "DESTINATION_ARN")
    destination_role = _config_value(source, "DestinationRole", "DESTINATION_ROLE", "")
    logs_filter = _config_value(source, "LogsFilter", "LOGS_FILTER", "")

    if not isinstance(destination_arn, str) or not destination_arn:
        raise ValueError("DestinationArn is required")
    destination_service = identify_arn_service(destination_arn)
    if destination_service not in ("lambda", "firehose"):
        raise ValueError(
            "DestinationArn must identify a Lambda or Firehose destination"
        )
    if destination_service == "firehose" and not destination_role:
        raise ValueError("DestinationRole is required for a firehose destination")
    if logs_filter is None:
        logs_filter = ""
    if not isinstance(logs_filter, str):
        raise ValueError("LogsFilter must be a string")

    disable_add_permission = _parse_bool(
        _config_value(
            source, "DisableAddPermission", "DISABLE_ADD_PERMISSION", "false"
        ),
        "DisableAddPermission",
    )
    add_permissions_to_all = _parse_bool(
        _config_value(
            source,
            "AddPermissionsToAllLogGroups",
            "ADD_PERMISSIONS_TO_ALL_LOG_GROUPS",
            "false",
        ),
        "AddPermissionsToAllLogGroups",
    )
    adopt_legacy_filters = _parse_bool(
        _config_value(source, "AdoptLegacyFilters", "ADOPT_LEGACY_FILTERS", "false"),
        "AdoptLegacyFilters",
    )
    if (
        not is_cloudformation
        and str(event.get("RequestType", "")).lower() == "reconcile"
        and "AdoptLegacyFilters" in event
    ):
        adopt_legacy_filters = _parse_direct_bool(
            event, "AdoptLegacyFilters", adopt_legacy_filters
        )

    prefix_value = _config_value(
        source, "LogGroupPermissionPrefix", "LOG_GROUP_PERMISSION_PREFIX", ""
    )
    if not isinstance(prefix_value, str):
        raise ValueError("LogGroupPermissionPrefix must be a comma-separated string")
    prefixes = tuple(
        prefix.strip() for prefix in prefix_value.split(",") if prefix.strip()
    )

    identity = _manager_identity(context)
    effective_destination_role = (
        destination_role or None if destination_service == "firehose" else None
    )
    config = ManagerConfig(
        regex_patterns=regex_patterns,
        destination_arn=destination_arn,
        destination_role=effective_destination_role,
        logs_filter=logs_filter,
        disable_add_permission=disable_add_permission,
        add_permissions_to_all_log_groups=add_permissions_to_all,
        log_group_permission_prefixes=prefixes,
        manager_lambda_arn=identity.manager_lambda_arn,
        managed_filter_name=identity.managed_filter_name,
        managed_tag_key=identity.managed_tag_key,
        managed_tag_value=_managed_tag_value(
            destination_arn,
            effective_destination_role,
            logs_filter,
            disable_add_permission,
            add_permissions_to_all,
            prefixes,
        ),
        adopt_legacy_filters=adopt_legacy_filters,
    )
    return config


def _matches(log_group_name: str, patterns: Tuple[Pattern[str], ...]) -> bool:
    return any(pattern.match(log_group_name) for pattern in patterns)


def _normalize_log_group_arn(log_group_arn: str) -> str:
    return log_group_arn[:-2] if log_group_arn.endswith(":*") else log_group_arn


def _log_group_name_from_arn(log_group_arn: str) -> str:
    marker = ":log-group:"
    if marker not in log_group_arn:
        raise ValueError(f"Invalid CloudWatch log group ARN: {log_group_arn}")
    return log_group_arn.split(marker, 1)[1]


def _log_group_arn(log_group: Dict[str, Any]) -> str:
    arn = log_group.get("logGroupArn") or log_group.get("arn")
    if not arn:
        raise ValueError(
            f"DescribeLogGroups omitted ARN for {log_group.get('logGroupName', 'unknown')}"
        )
    return _normalize_log_group_arn(arn)


def _event_log_group_arn(log_group_name: str, manager_lambda_arn: str) -> str:
    parts = manager_lambda_arn.split(":")
    return f"arn:{parts[1]}:logs:{parts[3]}:{parts[4]}:log-group:{log_group_name}"


def _discover_indexed_log_groups(
    identity: ManagerIdentity,
) -> Dict[str, Optional[str]]:
    indexed = {}
    pagination_token = None
    while True:
        request = {
            "ResourceTypeFilters": ["logs:log-group"],
            "TagFilters": [{"Key": identity.managed_tag_key}],
            "ResourcesPerPage": 100,
        }
        if pagination_token:
            request["PaginationToken"] = pagination_token
        response = tagging_client.get_resources(**request)
        for resource in response.get("ResourceTagMappingList", []):
            resource_arn = _normalize_log_group_arn(resource["ResourceARN"])
            tag_value = next(
                (
                    tag.get("Value")
                    for tag in resource.get("Tags", [])
                    if tag.get("Key") == identity.managed_tag_key
                ),
                None,
            )
            indexed[resource_arn] = tag_value
        pagination_token = response.get("PaginationToken")
        if not pagination_token:
            return indexed


def _list_standard_log_groups() -> Dict[str, str]:
    log_groups = {}
    next_token = None
    while True:
        request = {"logGroupClass": SUPPORTED_LOG_GROUP_CLASS, "limit": 50}
        if next_token:
            request["nextToken"] = next_token
        response = cloudwatch_logs.describe_log_groups(**request)
        for log_group in response.get("logGroups", []):
            log_groups[_log_group_arn(log_group)] = log_group["logGroupName"]
        next_token = response.get("nextToken")
        if not next_token:
            return log_groups


def _error_code(error: Exception) -> str:
    response = getattr(error, "response", {})
    if isinstance(response, dict):
        return response.get("Error", {}).get("Code", error.__class__.__name__)
    return error.__class__.__name__


def _call_logs_api(operation: str, **kwargs):
    lock = _logs_api_rate_locks[operation]
    with lock:
        delay = _logs_api_next_call[operation] - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _logs_api_next_call[operation] = (
            time.monotonic() + LOGS_API_MIN_INTERVAL_SECONDS
        )
    return getattr(cloudwatch_logs, operation)(**kwargs)


def _run_parallel(
    items: List[WorkItem], operation: Callable[[WorkItem], ReconciliationResult]
) -> ReconciliationResult:
    result = ReconciliationResult()
    if not items:
        return result

    executor = ThreadPoolExecutor(max_workers=MAX_RECONCILIATION_WORKERS)
    item_iterator = iter(items)
    pending = {}

    def submit_next() -> None:
        try:
            item = next(item_iterator)
        except StopIteration:
            return
        pending[executor.submit(operation, item)] = item

    succeeded = False
    try:
        for _ in range(min(MAX_RECONCILIATION_WORKERS, len(items))):
            submit_next()

        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                del pending[future]
            completed_results = [future.result() for future in completed]
            for completed_result in completed_results:
                result.add(completed_result)
            for _ in completed_results:
                submit_next()
        succeeded = True
    finally:
        if not succeeded:
            for future in pending:
                future.cancel()
        executor.shutdown(wait=True, cancel_futures=not succeeded)
    return result


def _put_subscription(log_group_name: str, config: ManagerConfig) -> None:
    request = {
        "destinationArn": config.destination_arn,
        "filterName": config.managed_filter_name,
        "filterPattern": config.logs_filter,
        "logGroupName": log_group_name,
    }
    if identify_arn_service(config.destination_arn) == "firehose":
        assert config.destination_role is not None
        request["roleArn"] = config.destination_role
    _call_logs_api("put_subscription_filter", **request)


def _delete_subscription(log_group_name: str, filter_name: str) -> None:
    _call_logs_api(
        "delete_subscription_filter",
        logGroupName=log_group_name,
        filterName=filter_name,
    )


def _tag_log_group(log_group_arn: str, config: ManagerConfig) -> None:
    _call_logs_api(
        "tag_resource",
        resourceArn=log_group_arn,
        tags={config.managed_tag_key: config.managed_tag_value},
    )


def _untag_log_group(log_group_arn: str, identity: ManagerIdentity) -> None:
    _call_logs_api(
        "untag_resource", resourceArn=log_group_arn, tagKeys=[identity.managed_tag_key]
    )


def _ensure_destination_permission(
    log_group_name: str,
    config: ManagerConfig,
    preserve_legacy_statement_id: bool = False,
    permission_cache: Optional[Set[Tuple[str, str]]] = None,
) -> None:
    if (
        identify_arn_service(config.destination_arn) != "lambda"
        or config.disable_add_permission
    ):
        return

    parts = config.manager_lambda_arn.split(":")
    region, account_id = parts[3], parts[4]
    if config.add_permissions_to_all_log_groups:
        permission_scope = "*"
    else:
        permission_scope = next(
            (
                f"{prefix}*"
                for prefix in config.log_group_permission_prefixes
                if log_group_name.startswith(prefix)
            ),
            log_group_name,
        )
    add_permission_to_lambda(
        config.destination_arn,
        permission_scope,
        region,
        account_id,
        preserve_legacy_statement_id=preserve_legacy_statement_id,
        permission_cache=permission_cache,
    )


def _filter_role(filter_data: Dict[str, Any], config: ManagerConfig) -> Optional[str]:
    if identify_arn_service(config.destination_arn) == "lambda":
        return None
    return filter_data.get("roleArn") or None


def _remove_stale_index(log_group_arn: str, config: ManagerConfig) -> None:
    _untag_log_group(log_group_arn, config)


def _reconcile_candidate(
    log_group_name: str,
    log_group_arn: str,
    config: ManagerConfig,
    indexed_value: Any,
    ensure_permission: bool = False,
    permission_cache: Optional[Set[Tuple[str, str]]] = None,
) -> ReconciliationResult:
    result = ReconciliationResult(inspected=1)
    response = _call_logs_api(
        "describe_subscription_filters", logGroupName=log_group_name
    )
    filters = response.get("subscriptionFilters") or []
    owned = next(
        (
            subscription_filter
            for subscription_filter in filters
            if subscription_filter.get("filterName") == config.managed_filter_name
        ),
        None,
    )

    if not _matches(log_group_name, config.regex_patterns):
        if owned:
            logger.info("Deleting managed subscription from %s", log_group_name)
            _delete_subscription(log_group_name, config.managed_filter_name)
            result.deleted = 1
        else:
            result.unchanged = 1
        _untag_log_group(log_group_arn, config)
        return result

    if owned:
        drifted = (
            owned.get("destinationArn") != config.destination_arn
            or owned.get("filterPattern", "") != config.logs_filter
            or _filter_role(owned, config) != config.destination_role
        )
        eligible_legacy = [
            subscription_filter
            for subscription_filter in filters
            if subscription_filter.get("destinationArn") == config.destination_arn
            and LEGACY_FILTER_PATTERN.fullmatch(
                subscription_filter.get("filterName", "")
            )
        ]
        conflicting = [
            subscription_filter
            for subscription_filter in filters
            if subscription_filter is not owned
            and subscription_filter.get("destinationArn") == config.destination_arn
            and subscription_filter not in eligible_legacy
        ]
        if conflicting:
            _remove_stale_index(log_group_arn, config)
            result.blocked = 1
            names = ", ".join(
                item.get("filterName", "<unnamed>") for item in conflicting
            )
            raise RuntimeError(
                f"Cannot manage {log_group_name}: same-destination filter is not adoptable: {names}"
            )
        if indexed_value == config.managed_tag_value and (
            drifted or (config.adopt_legacy_filters and eligible_legacy)
        ):
            _untag_log_group(log_group_arn, config)
            indexed_value = INDEX_NOT_PRESENT
        if drifted or ensure_permission:
            _ensure_destination_permission(
                log_group_name, config, permission_cache=permission_cache
            )
        if drifted:
            logger.info("Updating managed subscription on %s", log_group_name)
            _put_subscription(log_group_name, config)
            result.updated = 1
        else:
            result.unchanged = 1
        if config.adopt_legacy_filters:
            for legacy_filter in eligible_legacy:
                _delete_subscription(log_group_name, legacy_filter["filterName"])
            result.legacy_adopted = len(eligible_legacy)
        elif eligible_legacy:
            result.legacy_skipped = len(eligible_legacy)
            logger.warning(
                "Managed subscription on %s still has %d legacy duplicate(s); enable "
                "AdoptLegacyFilters to finish migration",
                log_group_name,
                len(eligible_legacy),
            )
        if indexed_value != config.managed_tag_value:
            _tag_log_group(log_group_arn, config)
        return result

    if indexed_value == config.managed_tag_value:
        _untag_log_group(log_group_arn, config)
        indexed_value = INDEX_NOT_PRESENT

    same_destination = [
        subscription_filter
        for subscription_filter in filters
        if subscription_filter.get("destinationArn") == config.destination_arn
    ]
    eligible_legacy = [
        subscription_filter
        for subscription_filter in same_destination
        if LEGACY_FILTER_PATTERN.fullmatch(subscription_filter.get("filterName", ""))
    ]
    conflicting = [
        subscription_filter
        for subscription_filter in same_destination
        if subscription_filter not in eligible_legacy
    ]

    if conflicting:
        _remove_stale_index(log_group_arn, config)
        result.blocked = 1
        names = ", ".join(item.get("filterName", "<unnamed>") for item in conflicting)
        raise RuntimeError(
            f"Cannot manage {log_group_name}: same-destination filter is not adoptable: {names}"
        )

    if eligible_legacy and not config.adopt_legacy_filters:
        _remove_stale_index(log_group_arn, config)
        result.legacy_skipped = len(eligible_legacy)
        logger.warning(
            "Leaving %d legacy subscription filter(s) on %s; enable AdoptLegacyFilters "
            "for an explicit migration",
            len(eligible_legacy),
            log_group_name,
        )
        return result

    if eligible_legacy:
        _ensure_destination_permission(
            log_group_name,
            config,
            preserve_legacy_statement_id=True,
            permission_cache=permission_cache,
        )
        deleted_before_put = []
        try:
            _put_subscription(log_group_name, config)
        except Exception as error:
            if _error_code(error) != "LimitExceededException":
                raise
            fallback_filter = eligible_legacy[0]
            logger.warning(
                "Subscription quota on %s requires deleting legacy filter %s before "
                "creating the deterministic replacement; forwarding may be interrupted",
                log_group_name,
                fallback_filter["filterName"],
            )
            _delete_subscription(log_group_name, fallback_filter["filterName"])
            deleted_before_put.append(fallback_filter["filterName"])
            _put_subscription(log_group_name, config)

        for legacy_filter in eligible_legacy:
            if legacy_filter["filterName"] not in deleted_before_put:
                _delete_subscription(log_group_name, legacy_filter["filterName"])
        _tag_log_group(log_group_arn, config)
        result.legacy_adopted = len(eligible_legacy)
        logger.info(
            "Migrated %d legacy subscription filter(s) on %s",
            len(eligible_legacy),
            log_group_name,
        )
        return result

    _ensure_destination_permission(
        log_group_name, config, permission_cache=permission_cache
    )
    try:
        _put_subscription(log_group_name, config)
    except Exception as error:
        if _error_code(error) == "LimitExceededException":
            _remove_stale_index(log_group_arn, config)
            result.blocked = 1
            raise RuntimeError(
                f"Cannot create managed subscription on {log_group_name}: subscription quota is full"
            ) from error
        raise
    _tag_log_group(log_group_arn, config)
    result.created = 1
    logger.info("Created managed subscription on %s", log_group_name)
    return result


def reconcile_subscriptions(
    config: ManagerConfig,
    context,
    repair: bool = False,
) -> ReconciliationResult:
    del context
    indexed = _discover_indexed_log_groups(config)
    log_groups = _list_standard_log_groups()
    indexed_standard = {
        arn: value for arn, value in indexed.items() if arn in log_groups
    }

    result = ReconciliationResult(
        scanned=len(log_groups), indexed=len(indexed_standard)
    )
    if repair:
        candidates = set(log_groups)
    else:
        matching = {
            arn
            for arn, log_group_name in log_groups.items()
            if _matches(log_group_name, config.regex_patterns)
        }
        current = (
            set()
            if config.adopt_legacy_filters
            else {
                arn
                for arn in matching
                if indexed_standard.get(arn, INDEX_NOT_PRESENT)
                == config.managed_tag_value
            }
        )
        candidates = (matching | set(indexed_standard)) - current
    result.unchanged = len(log_groups) - len(candidates)

    candidate_items = [
        (
            log_groups[log_group_arn],
            log_group_arn,
            indexed_standard.get(log_group_arn, INDEX_NOT_PRESENT),
        )
        for log_group_arn in sorted(candidates, key=lambda arn: log_groups[arn])
    ]
    permission_cache: Set[Tuple[str, str]] = set()
    result.add(
        _run_parallel(
            candidate_items,
            lambda item: _reconcile_candidate(
                item[0],
                item[1],
                config,
                item[2],
                ensure_permission=(repair or item[2] != config.managed_tag_value),
                permission_cache=permission_cache,
            ),
        )
    )

    logger.info(
        "Reconciliation complete: scanned=%d indexed=%d inspected=%d created=%d "
        "updated=%d deleted=%d unchanged=%d legacyAdopted=%d legacySkipped=%d blocked=%d",
        result.scanned,
        result.indexed,
        result.inspected,
        result.created,
        result.updated,
        result.deleted,
        result.unchanged,
        result.legacy_adopted,
        result.legacy_skipped,
        result.blocked,
    )
    return result


def reconcile_log_group(
    log_group_name: str, config: ManagerConfig, context
) -> ReconciliationResult:
    del context
    if not _matches(log_group_name, config.regex_patterns):
        return ReconciliationResult(scanned=1, unchanged=1)
    log_group_arn = _event_log_group_arn(log_group_name, config.manager_lambda_arn)
    result = ReconciliationResult(scanned=1)
    permission_cache: Set[Tuple[str, str]] = set()
    result.add(
        _reconcile_candidate(
            log_group_name,
            log_group_arn,
            config,
            INDEX_NOT_PRESENT,
            ensure_permission=True,
            permission_cache=permission_cache,
        )
    )
    return result


def _cleanup_indexed_log_group(
    log_group_arn: str, identity: ManagerIdentity
) -> ReconciliationResult:
    result = ReconciliationResult(scanned=1)
    log_group_name = _log_group_name_from_arn(log_group_arn)
    try:
        _delete_subscription(log_group_name, identity.managed_filter_name)
        result.deleted = 1
    except Exception as error:
        if _error_code(error) != "ResourceNotFoundException":
            raise
        result.unchanged = 1

    try:
        _untag_log_group(log_group_arn, identity)
    except Exception as error:
        if _error_code(error) != "ResourceNotFoundException":
            raise
    return result


def cleanup_managed_subscriptions(
    identity: ManagerIdentity,
) -> ReconciliationResult:
    indexed = _discover_indexed_log_groups(identity)
    result = ReconciliationResult(indexed=len(indexed))
    result.add(
        _run_parallel(
            sorted(indexed),
            lambda log_group_arn: _cleanup_indexed_log_group(log_group_arn, identity),
        )
    )

    logger.info(
        "Cleanup complete: scanned=%d indexed=%d inspected=%d deleted=%d unchanged=%d",
        result.scanned,
        result.indexed,
        result.inspected,
        result.deleted,
        result.unchanged,
    )
    return result


def _summary(
    request_type: str, identity: ManagerIdentity, result: ReconciliationResult
) -> Dict[str, Any]:
    values = asdict(result)
    return {
        "status": "SUCCESS",
        "requestType": request_type,
        "filterName": identity.managed_filter_name,
        "scanned": values["scanned"],
        "indexed": values["indexed"],
        "inspected": values["inspected"],
        "created": values["created"],
        "updated": values["updated"],
        "deleted": values["deleted"],
        "unchanged": values["unchanged"],
        "legacyAdopted": values["legacy_adopted"],
        "legacySkipped": values["legacy_skipped"],
        "blocked": values["blocked"],
    }


def _physical_resource_id(event: Dict[str, Any], context) -> str:
    if event.get("PhysicalResourceId"):
        return event["PhysicalResourceId"]
    manager_arn = unqualified_lambda_arn(context.invoked_function_arn)
    digest = hashlib.sha256(manager_arn.encode("utf-8")).hexdigest()
    return f"lambda-manager-reconciler-{digest}"


def _terraform_action(event: Dict[str, Any]) -> Optional[str]:
    lifecycle = event.get("tf")
    if lifecycle is None:
        return None
    if not isinstance(lifecycle, dict) or lifecycle.get("action") not in (
        "create",
        "update",
        "delete",
    ):
        raise ValueError("tf.action must be create, update, or delete")
    return lifecycle["action"]


def lambda_handler(event: Dict[str, Any], context):
    if not isinstance(event, dict):
        raise ValueError("Lambda event must be an object")

    if _is_cloudformation_event(event):
        request_type = event.get("RequestType")
        physical_resource_id = _physical_resource_id(event, context)
        try:
            if request_type not in ("Create", "Update", "Delete"):
                raise ValueError(
                    f"Unsupported CloudFormation RequestType: {request_type}"
                )
            if request_type == "Delete":
                identity = _manager_identity(context)
                result = cleanup_managed_subscriptions(identity)
            else:
                identity = load_config(event, context)
                result = reconcile_subscriptions(identity, context)
            response = _summary(request_type, identity, result)
            cfnresponse.send(
                event,
                context,
                cfnresponse.SUCCESS,
                response,
                physical_resource_id,
            )
            return response
        except Exception as error:
            logger.exception("CloudFormation %s reconciliation failed", request_type)
            failure = {"status": "FAILED", "requestType": request_type}
            cfnresponse.send(
                event,
                context,
                cfnresponse.FAILED,
                failure,
                physical_resource_id,
                reason=str(error)[:512],
            )
            return failure

    request_type = event.get("RequestType")
    if isinstance(request_type, str) and request_type.lower() == "reconcile":
        try:
            if _terraform_action(event) == "delete":
                identity = _manager_identity(context)
                result = cleanup_managed_subscriptions(identity)
                return _summary("Cleanup", identity, result)
            config = load_config(event, context)
            repair = _parse_direct_bool(event, "Repair", False)
            result = reconcile_subscriptions(config, context, repair=repair)
            return _summary("Reconcile", config, result)
        except Exception:
            logger.exception("Direct reconciliation failed")
            raise

    if isinstance(request_type, str) and request_type.lower() == "cleanup":
        try:
            identity = _manager_identity(context)
            result = cleanup_managed_subscriptions(identity)
            return _summary("Cleanup", identity, result)
        except Exception:
            logger.exception("Direct cleanup failed")
            raise

    detail = event.get("detail")
    if isinstance(detail, dict) and detail.get("eventName") == "CreateLogGroup":
        request_parameters = detail.get("requestParameters") or {}
        log_group_name = request_parameters.get("logGroupName")
        if not log_group_name:
            raise ValueError(
                "CreateLogGroup event is missing detail.requestParameters.logGroupName"
            )
        if cloudtrail_event_failed(detail):
            logger.info(
                "Skipping failed CloudTrail CreateLogGroup event for %s", log_group_name
            )
            return None
        if not should_process_log_group_class(detail):
            return None
        config = load_config(event, context)
        result = reconcile_log_group(log_group_name, config, context)
        return _summary("CreateLogGroup", config, result)

    raise ValueError(
        "Unsupported event: expected a CloudFormation custom resource, "
        '{"RequestType":"Reconcile"}, {"RequestType":"Cleanup"}, '
        "or a CreateLogGroup event"
    )


def cloudtrail_event_failed(event_detail: Dict[str, Any]) -> bool:
    return bool(event_detail.get("errorCode") or event_detail.get("errorMessage"))


def should_process_log_group_class(event_detail: Dict[str, Any]) -> bool:
    log_group_class = event_detail.get("requestParameters", {}).get(
        "logGroupClass", SUPPORTED_LOG_GROUP_CLASS
    )
    if log_group_class == SUPPORTED_LOG_GROUP_CLASS:
        return True
    logger.info(
        "Skipping log group because logGroupClass %s is not supported", log_group_class
    )
    return False


def add_permission_to_lambda(
    destination_arn: str,
    log_group_name: str,
    region: str,
    account_id: str,
    preserve_legacy_statement_id: bool = False,
    permission_cache: Optional[Set[Tuple[str, str]]] = None,
) -> None:
    permission_identity = f"{region}:{account_id}:{log_group_name}"
    statement_digest = hashlib.sha256(permission_identity.encode("utf-8")).hexdigest()
    legacy_statement_id = "allow-trigger-from-" + re.sub(
        r"[^a-zA-Z0-9\-_]", "-", log_group_name
    )
    statement_id = (
        legacy_statement_id
        if preserve_legacy_statement_id and len(legacy_statement_id) <= 100
        else f"allow-trigger-from-{statement_digest}"
    )
    partition = destination_arn.split(":", 2)[1]
    cache_key = (destination_arn, statement_id)
    with _lambda_permission_lock:
        if permission_cache is not None and cache_key in permission_cache:
            return
        try:
            lambda_client.add_permission(
                FunctionName=destination_arn,
                StatementId=statement_id,
                Action="lambda:InvokeFunction",
                Principal="logs.amazonaws.com",
                SourceArn=(
                    f"arn:{partition}:logs:{region}:{account_id}:log-group:"
                    f"{log_group_name}:*"
                ),
            )
            logger.info(
                "Added destination Lambda permission for log group scope %s",
                log_group_name,
            )
            if permission_cache is not None:
                permission_cache.add(cache_key)
        except Exception as error:
            if _error_code(error) == "ResourceConflictException":
                logger.info(
                    "Destination Lambda permission already exists for log group scope %s",
                    log_group_name,
                )
                if permission_cache is not None:
                    permission_cache.add(cache_key)
                return
            raise


def check_if_log_group_exist_in_log_group_permission_prefix(
    log_group_name: str, log_group_permission_prefix: List[str]
) -> bool:
    return any(
        prefix and log_group_name.startswith(prefix)
        for prefix in log_group_permission_prefix
    )


def identify_arn_service(arn: str) -> str:
    arn_parts = arn.split(":")
    if len(arn_parts) < 6:
        return "Invalid ARN format"
    service = arn_parts[2]
    if service in ("lambda", "firehose"):
        return service
    return "Unknown AWS Service"
