# AWS Lambda functions for integration with Coralogix

### ⚠️ Deprecated Integrations Removed

Deprecated integrations have been removed from this repository.

**For historical reference**, the complete code and documentation for these deprecated integrations is preserved in the [`deprecated-integrations-archive`](https://github.com/coralogix/coralogix-aws-serverless/tree/deprecated-integrations-archive) branch.

## Published Lambda Versioning

These rules apply to the published lambda packages under `src/<name>/`.

### Versioning expectations

- `Metadata.AWS::ServerlessRepo::Application.SemanticVersion` in `template.yaml` is the single source of truth for the published package version.
- Bump `SemanticVersion` whenever a published package changes beyond `CHANGELOG.md`.
- Do not try to reuse a previously published version number. AWS SAR versions are immutable, so fixes after a bad publish must ship as a new version on a new commit.

### Changelog expectations

- Each published package must keep `src/<name>/CHANGELOG.md`.
- The first release heading must be `## [X.Y.Z] - YYYY-MM-DD`.
- `X.Y.Z` in that first heading must match `template.yaml` `SemanticVersion`.
- The top release entry must include at least one bullet describing the release.
- A changelog-only edit does not require a `SemanticVersion` bump.
- Use the `skip-changelog` PR label only when a package change does not require a changelog entry or version bump.

### Publishing expectations

- Merge to `master` does not publish by itself.
- Promotion happens after merge by pushing a package release tag on the merged `master` commit you want to release.
- Accepted publish tags are `<name>-v<X.Y.Z>` and `<name>-<X.Y.Z>`.
- Both tag forms trigger the same single-package SAR publish workflow.
- `<name>-v<X.Y.Z>` is the canonical outward release identity and the GitHub Release name.
- If the bare alias tag is pushed first, the workflow backfills the canonical `<name>-v<X.Y.Z>` tag and creates the GitHub Release there.

### Maintainer flow

1. Merge the package change to `master`.
2. Validate the merged commit you intend to promote.
3. Confirm `src/<name>/template.yaml` `SemanticVersion` and the top `src/<name>/CHANGELOG.md` entry both match `X.Y.Z`.
4. Push either `git tag <name>-v<X.Y.Z>` or `git tag <name>-<X.Y.Z>` on that merged commit.
5. Run `git push origin <tag>` to trigger the publish workflow.
