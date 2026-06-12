#!/usr/bin/env bash

set -euo pipefail

tag_ref="${1:-}"

fail() {
  echo "release_tag_resolve: $*" >&2
  exit 1
}

if [[ -z "$tag_ref" ]]; then
  fail "usage: scripts/release_tag_resolve.sh <tag-or-ref>"
fi

trigger_tag="${tag_ref#refs/tags/}"

canonical_pattern='^([A-Za-z0-9][A-Za-z0-9-]*)-v([0-9]+\.[0-9]+\.[0-9]+)$'
alias_pattern='^([A-Za-z0-9][A-Za-z0-9-]*)-([0-9]+\.[0-9]+\.[0-9]+)$'

if [[ "$trigger_tag" =~ $canonical_pattern ]]; then
  package="${BASH_REMATCH[1]}"
  version="${BASH_REMATCH[2]}"
  tag_variant="canonical"
elif [[ "$trigger_tag" =~ $alias_pattern ]]; then
  package="${BASH_REMATCH[1]}"
  version="${BASH_REMATCH[2]}"
  tag_variant="alias"
else
  fail "tag '$trigger_tag' must match <package>-v<X.Y.Z> or <package>-<X.Y.Z>"
fi

canonical_tag="${package}-v${version}"

printf 'trigger_tag=%s\n' "$trigger_tag"
printf 'package=%s\n' "$package"
printf 'version=%s\n' "$version"
printf 'canonical_tag=%s\n' "$canonical_tag"
printf 'tag_variant=%s\n' "$tag_variant"
