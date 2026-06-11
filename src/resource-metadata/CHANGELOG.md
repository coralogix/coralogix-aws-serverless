# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [1.2.12] - 2025-12-04
### Changed
- Update the Node.js runtime to 22.x.

## [1.2.11] - 2024-10-15
### Fixed
- Fix the condition that excludes EC2 and Lambda resources.

## [1.2.10] - 2024-10-09
### Added
- Add AP3 to the supported region list.

### Changed
- Add a resource-type filter so either Lambda or EC2 resources can be excluded.

## [1.2.9] - 2024-05-21
### Changed
- Align region names with the rest of the integrations, for example `EU1` and `EU2`.

## [1.2.8] - 2024-02-08
### Changed
- Update dependencies and remove Jest and Babel.

## [1.2.7] - 2023-12-13
### Fixed
- Correct tag-to-attribute conversion.

## [1.2.6] - 2023-12-13
### Changed
- Keep the function running even when it cannot collect metadata for some Lambda functions.

## [1.2.5] - 2023-12-07
### Added
- Add filtering for Lambda functions.

## [0.0.2] - 2023-10-02
### Changed
- Switch the integration from the SSM option to AWS Secrets Manager terminology and behavior.

## [0.0.1] - 2023-08-16
### Added
- Allow using an existing secret instead of creating one automatically and remove the `SsmEnabled` parameter.
