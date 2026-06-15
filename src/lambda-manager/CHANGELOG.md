# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [2.0.12] - 2026-06-15
### Fixed
- Match CloudFormation `CreateLogGroup` events when `LogGroupClass` is omitted and the log group still defaults to `STANDARD`.
- Continue skipping non-standard `INFREQUENT_ACCESS` and `DELIVERY` log groups during create-event processing.

## [2.0.11] - 2026-06-13
### Fixed
- Ignore failed CloudTrail `CreateLogGroup` events so they do not trigger duplicate subscription work.
- Skip creating a new subscription when the destination is already attached to the log group.

## [2.0.10] - 2025-06-23
### Changed
- Remove duplicated code.
- Add a description for each function.
- Change the logging format and remove unnecessary logs.
- Improve Lambda runtime behavior.

## [2.0.9] - 2025-05-11
### Added
- Add the `AddPermissionsToAllLogGroups` parameter to grant subscription permissions to the destination for all current and future log groups using a wildcard.

## [2.0.8] - 2025-04-30
### Added
- Add the `DisableAddPermission` parameter for environments that use a custom permission policy.

## [2.0.7] - 2025-04-20
### Fixed
- Exclude non-standard log groups from processing.

## [2.0.6] - 2025-04-15
### Fixed
- Remove the backslash from the default `RegexPattern` value.
- Update the Lambda code to stay compatible with Terraform-triggered requests.

## [2.0.5] - 2025-02-17
### Fixed
- Remove the wildcard from the Lambda permission policy.
- Update the Lambda name format to `${stack_name}-LambdaFunction`.

## [2.0.4] - 2024-07-01
### Fixed
- Add boto3 configuration so the Lambda can handle `ThrottlingException`.
- Improve Lambda error handling.

## [2.0.3] - 2024-06-26
### Added
- Add the `LogGroupPermissionPreFix` parameter so one permission can cover all matching log groups under a configured prefix.

## [2.0.2] - 2024-06-24
### Added
- Trigger the Lambda on stack creation when `ScanOldLogGroups` is set to `true`.

## [2.0.1] - 2024-02-04
### Changed
- Update the Lambda code so it no longer requires the allow-all policy.

## [2.0.0] - 2024-02-20
### Added
- Support Lambda as a destination.
- Scan existing log groups and process them.

### Changed
- Stop deploying the Firehose stream as part of the CloudFormation template.
- Stop creating destination permissions automatically in the CloudFormation template.
- Rename environment variables for the new deployment model.
