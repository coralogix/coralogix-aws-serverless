# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [1.0.4] - 2026-08-13
### Added
- Add optional `SnsKmsKeyArn` to encrypt the Lambda failure-notification SNS topic with a customer-managed KMS key.
### Fixed
- Reuse the SAM OnFailure topic logical ID so existing email subscriptions are not replaced when `SnsKmsKeyArn` is unset.

## [1.0.3] - 2023-08-09
### Fixed
- Fix the Salesforce API update flow.

## [1.0.2] - 2023-07-30
### Added
- Add US2 region support.

## [1.0.1] - 2023-03-27
### Added
- Add ingress support.

## [1.0.0] - 2022-12-15
### Added
- Initial Salesforce event-log integration.
