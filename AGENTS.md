# Release Conventions For Coding Agents

Use this file when changing published lambda packages under `src/<name>/` or the workflows that release them.

## Versioning

- Treat `Metadata.AWS::ServerlessRepo::Application.SemanticVersion` in `src/<name>/template.yaml` as the only published version source of truth.
- If a published package changes beyond `CHANGELOG.md`, bump `SemanticVersion`.
- Do not reuse an old published version number. AWS SAR versions are immutable, so any fix after publish must move to a new version on a new commit.

## Changelog

- Keep `src/<name>/CHANGELOG.md` for every published package.
- The first release heading must be `## [X.Y.Z] - YYYY-MM-DD`.
- The top changelog version must match `template.yaml` `SemanticVersion`.
- The top release entry must contain at least one bullet.
- Changelog-only edits do not require a `SemanticVersion` bump.
- Use the `skip-changelog` PR label only when a package change does not require either a changelog entry or a version bump.

## Publishing

- Merge to `master` does not publish a package.
- Publishing is triggered by pushing a package tag on the merged `master` commit you want to promote.
- Accepted trigger tags are `<name>-v<X.Y.Z>` and `<name>-<X.Y.Z>`.
- Both tag forms publish the same package version, but `<name>-v<X.Y.Z>` is the canonical GitHub Release identity.
- If the bare alias tag is pushed first, the workflow backfills the canonical `<name>-v<X.Y.Z>` tag after successful publish.

## Maintainer Flow

1. Merge the package change to `master`.
2. Validate the merged commit you want to promote.
3. Confirm `src/<name>/template.yaml` `SemanticVersion` matches the top `src/<name>/CHANGELOG.md` release.
4. Push either `git tag <name>-v<X.Y.Z>` or `git tag <name>-<X.Y.Z>` on that merged commit.
5. Push the tag to `origin` to trigger publishing.
