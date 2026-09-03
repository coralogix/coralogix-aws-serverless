# Coralogix Lambda Manager

Lambda Manager keeps CloudWatch Logs subscription filters in sync for matching `STANDARD` log groups. It forwards logs to a Lambda or Firehose destination and automatically handles existing and newly created log groups.

## Configuration

| Parameter | Environment variable | Description | Default Value | Required |
|---|---|---|---|---|
| `RegexPattern` | `REGEX_PATTERN` | Comma-separated log-group name regular expressions; at least one expression is required. | `/aws/lambda/.*` | No |
| `LogsFilter` | `LOGS_FILTER` | CloudWatch Logs subscription filter pattern. | Empty | No |
| `DestinationArn` | `DESTINATION_ARN` | Destination Lambda function or Firehose delivery stream ARN. | None | Yes |
| `DestinationRole` | `DESTINATION_ROLE` | IAM role CloudWatch Logs assumes for a Firehose destination. | Empty | Firehose only |
| `DestinationType` | N/A | CloudFormation destination type used to configure IAM permissions. It must match `DestinationArn`; direct deployments derive the type from the ARN. | None | CloudFormation only |
| `DisableAddPermission` | `DISABLE_ADD_PERMISSION` | Do not modify the destination Lambda policy. Use when CloudWatch Logs invoke permissions are managed separately. | `false` | No |
| `AddPermissionsToAllLogGroups` | `ADD_PERMISSIONS_TO_ALL_LOG_GROUPS` | Allow CloudWatch Logs from any log group in the account and region through one broad destination Lambda permission. | `false` | No |
| `LogGroupPermissionPrefix` | `LOG_GROUP_PERMISSION_PREFIX` | Comma-separated prefixes whose matching groups share destination Lambda permissions. | Empty | No |
| `AdoptLegacyFilters` | `ADOPT_LEGACY_FILTERS` | Explicitly migrate matching historical UUID-named filters. | `false` | No |
| `AWSApiRequestsLimit` | `AWS_API_REQUESTS_LIMIT` | AWS API retry attempt limit. | `10` | No |
| `FunctionMemorySize` | N/A | Memory allocated to the Lambda Manager function. Consult Coralogix support before lowering it. | `1024` | No |
| `FunctionTimeout` | N/A | Lambda Manager timeout in seconds. Consult Coralogix support before lowering it. | `900` | No |
| `NotificationEmail` | N/A | Email address for failure notifications. | Empty | No |
| `SnsKmsKeyArn` | N/A | KMS key ARN used to encrypt the failure-notification SNS topic. | Empty | No |

`LogGroupPermissionPrefix` reduces the number of resource-policy statements on a Lambda destination by creating one permission for each configured prefix instead of one per log group. This is useful for destinations receiving logs from many groups. Permission requests for a shared prefix or the all-log-groups wildcard are deduplicated within each reconciliation. Prefix-based permissions may not appear as individual triggers in the destination Lambda console.

`SnsKmsKeyArn` must be a KMS key ARN, not an alias. Its policy must allow `sns.amazonaws.com` and the Lambda execution role to use `kms:Decrypt` and `kms:GenerateDataKey*`.

Every explicit reconciliation scans existing `STANDARD` log groups.

## Reconciliation

The canonical synchronous invocation is:

```json
{"RequestType":"Reconcile"}
```

The response is a bounded summary containing `scanned`, `indexed`, `inspected`, `created`, `updated`, `deleted`, `unchanged`, `legacyAdopted`, `legacySkipped`, and `blocked`. Treat Lambda `FunctionError` or a response whose `status` is not `SUCCESS` as a deployment failure.

Treat every configuration change as incomplete until reconciliation returns `status=SUCCESS` without a Lambda `FunctionError`. After any failed reconciliation, fix the cause and rerun it successfully before changing configuration again, deleting the stack, or replacing the manager function. Stack deletion relies on the manager tag index and cannot discover a filter whose tag was never written successfully.

The manager never creates or updates its filter to a destination already used by an unrelated filter on the same log group. Reconciliation fails without modifying either filter. Recognized legacy Coralogix filters remain governed by `AdoptLegacyFilters`.

The manager tag stores a hash of the destination ARN, effective Firehose role, log filter, and Lambda permission settings. Normal reconciliation skips subscription lookups and permission updates for matching groups whose tag already has the current hash. A configuration change or missing/stale tag causes the group to be inspected, ensures the requested destination permission for an existing filter, and updates the tag only after reconciliation succeeds. Enabling legacy adoption temporarily bypasses the subscription fast path so eligible legacy filters remain discoverable, but does not add permission calls when the configuration hash is already current; disabling adoption does not invalidate the configuration hash.

Use `Repair` only after manager index tags were manually removed or changed, or for periodic ownership auditing:

```json
{"RequestType":"Reconcile","Repair":true}
```

Repair ignores the configuration-hash optimization and inspects every `STANDARD` group. Use it to find manual filter changes, recover an untagged deterministic filter that no longer matches, or audit ownership. Repair never broadens legacy adoption beyond groups matching the current regex.

The manager derives ownership from its unqualified function ARN. Keep the function name stable. Aliases, versions, code, and configuration updates preserve ownership; renaming or moving the function creates a new ownership namespace. Reconcile or delete the old deployment before renaming it, otherwise its deterministic filters remain unmanaged.

The packaged function reserves one concurrent Lambda execution to prevent overlapping reconciliations from writing conflicting filter and tag state. Each reconciliation still processes independent log groups concurrently within that execution.

## CloudFormation and SAM

Stack creation and relevant updates automatically reconcile through `Custom::LambdaTrigger`. The custom resource receives every behavior-changing setting plus a reconciler version, so code-only reconciler releases also trigger an update. Stack deletion queries only this manager's tag index, deletes its exact deterministic filter from each indexed group, and then removes the tag. It does not scan every account log group.

Use stack outputs `LambdaManagerFunctionName` and `LambdaManagerFunctionArn` for out-of-band synchronous invocation and `lambda:InvokeFunction` grants. Direct `Create`, `Update`, and `Delete` payloads are not supported; those operations are accepted only in a complete CloudFormation custom-resource envelope.

Example invocation:

```bash
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --invocation-type RequestResponse \
  --cli-binary-format raw-in-base64-out \
  --payload '{"RequestType":"Reconcile"}' \
  response.json
```

## Legacy Filter Adoption

Historical releases used names such as `Coralogix_Filter_<UUID>`, which do not prove which manager created them. Adoption is therefore explicit and limited to filters that:

- are on a group matching the unchanged current regex;
- exactly match the historical UUID name format; and
- use the configured destination ARN.

AWS cannot rename a subscription filter. Adoption creates the deterministic replacement, removes the selected UUID filter, and then writes the manager index tag. If the service rejects the additional filter at the active quota, the manager deletes the eligible legacy filter and retries once, which can cause a temporary forwarding gap.

Do not change regex, log filter, destination ARN/role, or permission settings while adopting. Historical managers could share a destination and overlapping regex scope, so review `legacyAdopted` before changing anything else. Nonmatching, malformed, and different-destination filters are intentionally untouched.

CloudFormation configuration-based adoption:

1. Upgrade with all behavior settings unchanged and set only `AdoptLegacyFilters=true`.
2. Verify the automatic reconciliation and review `legacyAdopted`.
3. Set only `AdoptLegacyFilters=false` in the next stack update.
4. Make other configuration changes only after adoption is disabled.

CloudFormation one-off adoption, preferred when possible:

1. Keep the stack parameter at `false`; the initial reconciliation reports eligible filters in `legacySkipped`.
2. Invoke `{"RequestType":"Reconcile","AdoptLegacyFilters":true}` synchronously.
3. Verify success and `legacyAdopted`. The stack parameter and Lambda environment remain `false`.

For direct deployments, the same two choices apply. Prefer the request-scoped override. If using `ADOPT_LEGACY_FILTERS=true`, change only that environment variable, invoke a body that omits `AdoptLegacyFilters`, verify migration, then restore it to `false` and invoke again. The function never mutates its own configuration to disable adoption.

## Direct Lambda Deployment

Package `lambda_function.py` with `requirements.txt`, use handler `lambda_function.lambda_handler` and Python 3.14, and configure the applicable environment variables above. Do not set `DESTINATION_TYPE`; the function derives it from `DESTINATION_ARN`. The execution role needs the template-equivalent CloudWatch Logs subscription and log-group tag permissions, `tag:GetResources`, conditional `lambda:AddPermission`, and conditional Firehose `iam:PassRole`. Configure EventBridge and its invoke permission separately if new log groups should be processed automatically.

Invoke synchronously after first deployment and after code, regex, filter, destination, destination role, permission mode/prefix, or adoption configuration changes. The caller needs `lambda:InvokeFunction`.

## Terraform

Use `aws_lambda_invocation`, not an invocation data source or `local-exec`. Keep `lifecycle_scope = "CREATE_ONLY"`; `CRUD` sends an incompatible lifecycle payload while dependencies are being destroyed.

```hcl
resource "aws_lambda_invocation" "lambda_manager_reconcile" {
  function_name = aws_lambda_function.lambda_manager.function_name
  input = jsonencode(merge(
    { RequestType = "Reconcile" },
    var.adopt_legacy_filters_once == null ? {} : {
      AdoptLegacyFilters = var.adopt_legacy_filters_once
    }
  ))
  lifecycle_scope = "CREATE_ONLY"

  triggers = {
    code = aws_lambda_function.lambda_manager.source_code_hash
    config = sha256(jsonencode({
      regex_pattern                 = var.regex_pattern
      logs_filter                   = var.logs_filter
      destination_arn               = var.destination_arn
      destination_role              = var.destination_role
      disable_add_permission        = var.disable_add_permission
      add_permissions_to_all_groups = var.add_permissions_to_all_log_groups
      log_group_permission_prefix   = var.log_group_permission_prefix
      adopt_legacy_filters_env      = var.adopt_legacy_filters
      adopt_legacy_filters_once     = var.adopt_legacy_filters_once
    }))
  }

  depends_on = [aws_iam_role_policy.lambda_manager]
}
```

Define `adopt_legacy_filters_once` as nullable with a default of `null`. For preferred one-off adoption, keep `ADOPT_LEGACY_FILTERS=false`, apply with only `adopt_legacy_filters_once=true`, verify `legacyAdopted`, then immediately apply with that variable reset to `null` or `false`. For configuration-based adoption, keep the request override `null`, apply with only the environment flag set to `true`, verify, then apply with only that flag restored to `false`. Change other behavior settings afterward.

Normal Terraform input should omit `Repair`. Run a separate operator-controlled synchronous invocation with `Repair=true` for index repair or auditing.

## Firehose Destination

Before using a Firehose destination, deploy the Coralogix integration described in the [AWS Firehose integration documentation](https://coralogix.com/docs/aws-firehose/).

CloudWatch Logs must be able to assume `DestinationRole`, and that role must be able to write to the configured delivery stream. A minimal permissions policy includes `firehose:PutRecord` and `firehose:PutRecordBatch` for that stream. Its trust policy must allow the regional CloudWatch Logs service principal, for example `logs.us-east-1.amazonaws.com`, to call `sts:AssumeRole`.

## License

This project is licensed under the Apache-2.0 License.
