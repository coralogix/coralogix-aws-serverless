# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [3.1.1] - 2026-08-17
### Fixed
- Upgrade `nodemailer` to `^9.0.5` to address GHSA-p6gq-j5cr-w38f.

## [3.1.0] - 2026-08-11
### Changed
- Send to the regional Coralogix domains (`api.<region>.coralogix.com`) instead of the legacy per-region domains.
- Update the Node.js runtime to 24.x, the latest AWS Lambda supports.

### Added
- Add `AP3` and `US3` to `CoralogixRegion`.

## [3.0.1] - 2026-08-13
### Added
- Add optional `SnsKmsKeyArn` to encrypt the Lambda failure-notification SNS topic with a customer-managed KMS key.
### Fixed
- Reuse the SAM OnFailure topic logical ID so existing email subscriptions are not replaced when `SnsKmsKeyArn` is unset.

## [3.0.0] - 2025-03-13
### Added
- Parse the OpenSearch JSON response in the templating flow and fail fast when the template result is empty.
- Make the search index configurable.

### Changed
- Replace the API endpoints and Coralogix region names with the current ones.
- Update the OpenSearch request flow to use the new endpoints, default variable handling, and authorization header.
- Upgrade the runtime from Node.js 20.x to 22.x.
- Upgrade dependencies.

### Fixed
- Rewrite the function from callbacks to async/await so the Lambda does not exit before the email is sent.
- Add more logs and error handling to simplify troubleshooting.
- Remove the unused IAM policy from the SAM template.

## [2.0.2] - 2024-03-01
### Fixed
- Add semantic versioning metadata.

## [2.0.1] - 2024-03-01
### Fixed
- Add the SES `sendmail` policy to the Lambda function.

## [2.0.0] - 2023-12-12
### Changed
- Move from Elasticsearch to OpenSearch and rename the package to `coralogix-reporter`.
- Upgrade the runtime from Node.js 16.x to 20.x.
