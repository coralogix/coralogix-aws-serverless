# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [0.3.2] - 2026-02-20
### Added
- Assume a cross-account IAM role when querying an AWS Config aggregator in a different account via the `ConfigCrossAccountRole` parameter.

### Fixed
- Mention `crossaccount.js` in `package.json` so it is included in the build output.

## [0.3.0] - 2025-05-05
### Added
- Support cross-account collection through both AWS Config and static account lists.
- Enable cross-account EventBridge event reception through the SQS queue.
- Filter functions by the telemetry-exporter layer.

### Changed
- Split StaticIAM configuration between the `CROSSACCOUNT_IAM_ACCOUNTIDS` and `CROSSACCOUNT_IAM_ROLE_NAME` environment variables.

### Fixed
- Stop using `GetFunctionCommand` in the collection flow to avoid exposing source-code links in command output.

## [0.2.0] - 2025-04-02
### Added
- Add support for collecting metadata across multiple regions and accounts.

### Fixed
- Align JavaScript line endings so files consistently end with semicolons.

## [0.1.4] - 2025-02-19
### Fixed
- Reduce the default EC2 batch size from 50 to 25 and make the chunk size configurable.

## [0.1.3] - 2025-02-17
### Fixed
- Rewrite EC2 batch collection to avoid exceeding the SQS message size limit.

## [0.1.2] - 2025-02-04
### Fixed
- Adjust the CloudTrail S3 bucket name so it stays within the 63-character limit.

## [0.1.1] - 2025-01-31
### Fixed
- Remove the non-existent function from the SAM template and hardcode the message retention period to one hour instead of using the resource TTL.
- Update the GitHub Actions publish step to store the multi-function SAM template.

## [0.1.0] - 2025-01-28
### Added
- Initial release.
