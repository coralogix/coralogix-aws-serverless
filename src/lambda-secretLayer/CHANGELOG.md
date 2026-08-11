# Changelog

All notable changes to this project will be documented in this file.
This format is based on Keep a Changelog.

## [1.1.0] - 2026-08-11
### Added
- Add `nodejs22.x` and `nodejs24.x` to the default `CompatibleRuntimes`, so the layer can be attached to functions on the current runtimes. `wrapper.sh` already routes anything other than Node.js 14/16 to the SDK v3 code path. The previously listed runtimes are unchanged.

### Fixed
- Store `wrapper.sh` as executable in `wrapper.zip`. Consumers set `AWS_LAMBDA_EXEC_WRAPPER=/opt/wrapper.sh` and Lambda execs that path, but the archive stored it `0644`, so the wrapper failed with exit 126 before the handler started.
- Rebuild `wrapper.zip` from the tracked wrapper sources. The archive had not been rebuilt since 2024-08-25, so #190's removal of a `console.log` of the Secrets Manager secret name never reached the deployed layer. Only the secret's name was logged, never its value.

## [1.0.3] - 2024-08-25
### Changed
- Allow the layer to run in Node.js 20 applications by using the Node.js 18-compatible code path.

## [1.0.2] - 2023-10-01
### Changed
- Switch the integration from the SSM option to AWS Secrets Manager terminology and behavior.

## [1.0.1] - 2023-08-15
### Added
- Allow using an existing secret instead of creating one automatically.

## [1.0.0] - 2023-03-08
### Added
- Introduce the secret layer for safe keeping of the Coralogix data API key.
