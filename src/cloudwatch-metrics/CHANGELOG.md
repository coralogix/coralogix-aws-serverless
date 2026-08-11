# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [1.1.0] - 2026-08-11
### Changed
- Send to the regional Coralogix domains (`ingress.<region>.coralogix.com`) instead of the legacy per-region domains.
- Post to `/logs/v1/singles` with an `Authorization: Bearer` header instead of the retired `/logs/rest/singles` path and `private_key` header. The `PrivateKey` parameter is unchanged; its value is now sent as the bearer token. The legacy path is not served on `US3`.
- Require the `CORALOGIX_URL` environment variable instead of falling back to `api.coralogix.com`, which does not serve the ingestion path. The template always sets it, so stack deployments are unaffected.
- Change the `CoralogixRegion` default from `Europe` to `EU1`. Both resolve to the same endpoint, so the deployed behaviour is identical.
- Update the Node.js runtime from 16.x, deprecated by AWS on 2024-06-12, to 24.x.
- Migrate from AWS SDK for JavaScript v2 to v3 (`@aws-sdk/client-cloudwatch`), which the runtime bump requires: no supported Node.js runtime ships SDK v2, and the function relied on the runtime to provide it. `@aws-sdk/client-cloudwatch` is now a declared dependency.

### Added
- Accept the region codes `EU1`, `EU2`, `AP1`, `AP2`, `AP3`, `US1`, `US2` and `US3` for `CoralogixRegion`, and add `AP3` and `US3` endpoint support.

### Deprecated
- The `Europe`, `Europe2`, `India`, `Singapore` and `US` values of `CoralogixRegion` are still accepted and map to `EU1`, `EU2`, `AP1`, `AP2` and `US1`. Use the region codes instead.

## [1.0.7] - 2023-07-30
### Added
- Add US2 region support.

## [1.0.6] - 2023-03-27
### Added
- Add ingress support for the integration.

## [1.0.5] - 2023-03-23
### Changed
- Align the published application version metadata.

## [1.0.4] - 2023-03-23
### Changed
- Remove UUID validation from the private key parameter.

## [1.0.3] - 2022-09-13
### Changed
- Upgrade the runtime to Node.js 16.x.

## [1.0.2] - 2022-09-12
### Changed
- Refresh the published package with the updated Node.js runtime.
