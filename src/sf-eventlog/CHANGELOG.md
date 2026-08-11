# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [1.1.0] - 2026-08-11
### Changed
- Send to the regional Coralogix domains (`ingress.<region>.coralogix.com`) instead of the legacy per-region domains.
- Post to `/logs/v1/singles` instead of `/api/v1/logs`, which Coralogix disables on 2026-09-30.
- Bump `coralogix_logger` to 2.1.1, which sends the private key as an `Authorization: Bearer` header and converts the bulk payload to the singles format. 2.0.5 sent no headers at all, so it could not authenticate against the replacement endpoint.
- Change the `CoralogixRegion` default from `Europe` to `EU1`. Both resolve to the same endpoint, so the deployed behaviour is identical.

### Added
- Accept the region codes `EU1`, `EU2`, `AP1`, `AP2`, `AP3`, `US1`, `US2` and `US3` for `CoralogixRegion`, and add `AP3` and `US3` endpoint support.

### Deprecated
- The `Europe`, `Europe2`, `India`, `Singapore` and `US` values of `CoralogixRegion` are still accepted and map to `EU1`, `EU2`, `AP1`, `AP2` and `US1`. Use the region codes instead.

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
