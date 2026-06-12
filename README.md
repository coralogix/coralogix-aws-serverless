# AWS Lambda functions for integration with Coralogix

### ⚠️ Deprecated Integrations Removed

Deprecated integrations have been removed from this repository.

**For historical reference**, the complete code and documentation for these deprecated integrations is preserved in the [`deprecated-integrations-archive`](https://github.com/coralogix/coralogix-aws-serverless/tree/deprecated-integrations-archive) branch.

## Published Lambda Versioning

For published lambda packages under `src/<name>/`:

- Bump `Metadata.AWS::ServerlessRepo::Application.SemanticVersion` in `template.yaml` whenever the package changes beyond `CHANGELOG.md`.
- Keep the first `CHANGELOG.md` release heading in `## [X.Y.Z] - YYYY-MM-DD` format, with `X.Y.Z` matching `SemanticVersion` and at least one bullet under that release.
- Merge to `master` does not publish by itself. Promotion happens after merge by pushing a per-package tag from the merged `master` commit you want to release.
- Accepted publish tags are `<name>-v<X.Y.Z>` and `<name>-<X.Y.Z>`. Both trigger the same single-package SAR publish flow, and `<name>-v<X.Y.Z>` is the canonical GitHub Release identity.
- Maintainer flow:
  1. Merge the package change to `master` and validate the merged commit.
  2. Confirm `src/<name>/template.yaml` `SemanticVersion` and the top `src/<name>/CHANGELOG.md` entry both match `X.Y.Z`.
  3. Push either `git tag <name>-v<X.Y.Z>` or `git tag <name>-<X.Y.Z>` on that merged commit, then `git push origin <tag>`.
  4. If the bare alias tag is pushed first, the workflow backfills the canonical `<name>-v<X.Y.Z>` tag and creates the GitHub Release there.
  5. If a published build has an issue, ship a new commit with a new `SemanticVersion`; AWS SAR versions are immutable and cannot be reused.
- Use the `skip-changelog` PR label only when a package change does not require a changelog entry or version bump.
