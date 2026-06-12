#!/usr/bin/env bash

set -euo pipefail

fail() {
  echo "release_publish_preflight_test: $*" >&2
  exit 1
}

get_value() {
  local key="$1"

  awk -F= -v key="$key" '$1 == key { print substr($0, length($1) + 2); exit }'
}

assert_eq() {
  local expected="$1"
  local actual="$2"
  local message="$3"

  [[ "$actual" == "$expected" ]] || fail "$message: expected '$expected', got '$actual'"
}

extract_semver() {
  local template_path="$1"

  sed -n 's/^[[:space:]]*SemanticVersion:[[:space:]]*//p' "$template_path" \
    | head -n1 \
    | tr -d '"\r' \
    | xargs
}

bump_patch_version() {
  local version="$1"
  local major minor patch

  IFS=. read -r major minor patch <<< "$version"
  [[ -n "$major" && -n "$minor" && -n "$patch" ]] || fail "invalid semantic version '$version'"

  printf '%s.%s.%s\n' "$major" "$minor" "$((patch + 1))"
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

resource_metadata_version="$(extract_semver src/resource-metadata/template.yaml)"
[[ -n "$resource_metadata_version" ]] || fail "could not extract resource-metadata SemanticVersion"

resource_metadata_tag="resource-metadata-v${resource_metadata_version}"
resource_metadata_alias_tag="resource-metadata-${resource_metadata_version}"
resource_metadata_mismatch_tag="resource-metadata-v$(bump_patch_version "$resource_metadata_version")"

canonical_output="$(bash scripts/release_tag_resolve.sh refs/tags/resource-metadata-v1.2.12)"
assert_eq "resource-metadata" "$(printf '%s\n' "$canonical_output" | get_value package)" "canonical tag package"
assert_eq "1.2.12" "$(printf '%s\n' "$canonical_output" | get_value version)" "canonical tag version"
assert_eq "resource-metadata-v1.2.12" "$(printf '%s\n' "$canonical_output" | get_value canonical_tag)" "canonical tag identity"
assert_eq "canonical" "$(printf '%s\n' "$canonical_output" | get_value tag_variant)" "canonical tag variant"

alias_output="$(bash scripts/release_tag_resolve.sh lambda-secretLayer-1.0.3)"
assert_eq "lambda-secretLayer" "$(printf '%s\n' "$alias_output" | get_value package)" "alias tag package"
assert_eq "1.0.3" "$(printf '%s\n' "$alias_output" | get_value version)" "alias tag version"
assert_eq "lambda-secretLayer-v1.0.3" "$(printf '%s\n' "$alias_output" | get_value canonical_tag)" "alias canonicalization"
assert_eq "alias" "$(printf '%s\n' "$alias_output" | get_value tag_variant)" "alias tag variant"

if bash scripts/release_tag_resolve.sh v1.2.3 >/dev/null 2>&1; then
  fail "expected invalid repo-wide tag to be rejected"
fi

preflight_output="$(bash scripts/release_publish_preflight.sh "$resource_metadata_tag" HEAD HEAD)"
assert_eq "Coralogix-Resource-Metadata" "$(printf '%s\n' "$preflight_output" | get_value application_name)" "preflight application name"
assert_eq "$resource_metadata_tag" "$(printf '%s\n' "$preflight_output" | get_value canonical_tag)" "preflight canonical tag"
assert_eq "$resource_metadata_version" "$(printf '%s\n' "$preflight_output" | get_value semantic_version)" "preflight semantic version"

alias_preflight_output="$(bash scripts/release_publish_preflight.sh "$resource_metadata_alias_tag" HEAD HEAD)"
assert_eq "$resource_metadata_tag" "$(printf '%s\n' "$alias_preflight_output" | get_value canonical_tag)" "alias preflight canonical tag"
assert_eq "alias" "$(printf '%s\n' "$alias_preflight_output" | get_value tag_variant)" "alias preflight variant"

if bash scripts/release_publish_preflight.sh "$resource_metadata_tag" HEAD^ HEAD >/dev/null 2>&1; then
  fail "expected non-master ancestry check to fail"
fi

if bash scripts/release_publish_preflight.sh "$resource_metadata_mismatch_tag" HEAD HEAD >/dev/null 2>&1; then
  fail "expected mismatched SemanticVersion check to fail"
fi

if bash scripts/release_publish_preflight.sh does-not-exist-v1.2.3 HEAD HEAD >/dev/null 2>&1; then
  fail "expected missing package check to fail"
fi

echo "release_publish_preflight_test: all checks passed"
