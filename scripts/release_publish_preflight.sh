#!/usr/bin/env bash

set -euo pipefail

tag_ref="${1:-}"
master_ref="${2:-origin/master}"
commit_ish="${3:-HEAD}"

fail() {
  echo "release_publish_preflight: $*" >&2
  exit 1
}

extract_semver_from_stream() {
  sed -n 's/^[[:space:]]*SemanticVersion:[[:space:]]*//p' \
    | head -n1 \
    | tr -d '"\r' \
    | xargs
}

extract_application_name() {
  local template_path="$1"

  awk '
    /^[[:space:]]{2}AWS::ServerlessRepo::Application:/ {
      in_app_block = 1
      next
    }
    in_app_block && /^[[:space:]]{2}[A-Za-z0-9:".-]+:/ {
      exit
    }
    in_app_block && /^[[:space:]]{4}Name:/ {
      sub(/^[[:space:]]*Name:[[:space:]]*/, "")
      gsub(/["\r]/, "")
      print
      exit
    }
  ' "$template_path" | xargs
}

if [[ -z "$tag_ref" ]]; then
  fail "usage: scripts/release_publish_preflight.sh <tag-or-ref> [master-ref] [commit-ish]"
fi

while IFS='=' read -r key value; do
  [[ -n "$key" ]] || continue
  case "$key" in
    trigger_tag) trigger_tag="$value" ;;
    package) package="$value" ;;
    version) version="$value" ;;
    canonical_tag) canonical_tag="$value" ;;
    tag_variant) tag_variant="$value" ;;
  esac
done < <(bash scripts/release_tag_resolve.sh "$tag_ref")

[[ -n "${package:-}" ]] || fail "could not resolve package from tag '$tag_ref'"
[[ -n "${version:-}" ]] || fail "could not resolve version from tag '$tag_ref'"
[[ -n "${trigger_tag:-}" ]] || fail "could not resolve trigger tag from '$tag_ref'"
[[ -n "${canonical_tag:-}" ]] || fail "could not resolve canonical tag from '$tag_ref'"
[[ -n "${tag_variant:-}" ]] || fail "could not resolve tag variant from '$tag_ref'"

package_dir="src/${package}"
template_path="${package_dir}/template.yaml"
changelog_path="${package_dir}/CHANGELOG.md"

git rev-parse --verify "$commit_ish" >/dev/null 2>&1 || fail "commit not found: $commit_ish"
git rev-parse --verify "$master_ref" >/dev/null 2>&1 || fail "master ref not found: $master_ref"

commit_sha="$(git rev-parse "$commit_ish")"
master_sha="$(git rev-parse "$master_ref")"
git merge-base --is-ancestor "$commit_sha" "$master_sha" \
  || fail "tagged commit $commit_sha is not reachable from $master_ref"

[[ -f "$template_path" ]] || fail "missing template file: $template_path"
[[ -f "$changelog_path" ]] || fail "missing changelog file: $changelog_path"

semantic_version="$(extract_semver_from_stream < "$template_path")"
[[ -n "$semantic_version" ]] || fail "could not read SemanticVersion from $template_path"
[[ "$semantic_version" == "$version" ]] \
  || fail "tag version $version does not match $template_path SemanticVersion $semantic_version"

application_name="$(extract_application_name "$template_path")"
[[ -n "$application_name" ]] || fail "could not read AWS::ServerlessRepo::Application.Name from $template_path"

bash scripts/changelog_release_notes.sh "$package_dir" "$version" >/dev/null

printf 'trigger_tag=%s\n' "$trigger_tag"
printf 'canonical_tag=%s\n' "$canonical_tag"
printf 'tag_variant=%s\n' "$tag_variant"
printf 'package=%s\n' "$package"
printf 'package_dir=%s\n' "$package_dir"
printf 'version=%s\n' "$version"
printf 'template_path=%s\n' "$template_path"
printf 'changelog_path=%s\n' "$changelog_path"
printf 'application_name=%s\n' "$application_name"
printf 'semantic_version=%s\n' "$semantic_version"
printf 'commit_sha=%s\n' "$commit_sha"
printf 'master_ref=%s\n' "$master_ref"
printf 'master_sha=%s\n' "$master_sha"
