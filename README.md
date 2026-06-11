# AWS Lambda functions for integration with Coralogix

### ⚠️ Deprecated Integrations Removed

Deprecated integrations have been removed from this repository.

**For historical reference**, the complete code and documentation for these deprecated integrations is preserved in the [`deprecated-integrations-archive`](https://github.com/coralogix/coralogix-aws-serverless/tree/deprecated-integrations-archive) branch.

## Published Lambda Versioning

For published lambda packages under `src/<name>/`:

- Bump `Metadata.AWS::ServerlessRepo::Application.SemanticVersion` in `template.yaml` whenever the package changes beyond `CHANGELOG.md`.
- Keep the first `CHANGELOG.md` release heading in `## [X.Y.Z] - YYYY-MM-DD` format, with `X.Y.Z` matching `SemanticVersion` and at least one bullet under that release.
- Merged releases create a per-package Git tag and GitHub Release in the form `<name>-v<X.Y.Z>`.
- Use the `skip-changelog` PR label only when a package change does not require a changelog entry or version bump.
