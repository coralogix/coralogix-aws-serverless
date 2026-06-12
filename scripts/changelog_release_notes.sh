#!/usr/bin/env bash

set -euo pipefail

package_dir="${1:-}"
requested_version="${2:-}"

fail() {
  echo "changelog_release_notes: $*" >&2
  exit 1
}

extract_semver_from_stream() {
  sed -n 's/^[[:space:]]*SemanticVersion:[[:space:]]*//p' \
    | head -n1 \
    | tr -d '"\r' \
    | xargs
}

if [[ -z "$package_dir" ]]; then
  fail "usage: scripts/changelog_release_notes.sh <src/package-dir> [version]"
fi

package_dir="${package_dir#./}"
package_dir="${package_dir%/}"
template_path="$package_dir/template.yaml"
changelog_path="$package_dir/CHANGELOG.md"

[[ -f "$template_path" ]] || fail "missing template file: $template_path"
[[ -f "$changelog_path" ]] || fail "missing changelog file: $changelog_path"

version="$requested_version"
if [[ -z "$version" ]]; then
  version="$(extract_semver_from_stream < "$template_path")"
fi

[[ -n "$version" ]] || fail "could not determine SemanticVersion for $package_dir"

section="$(
  awk -v version="$version" '
    BEGIN {
      target = "## [" version "] - "
      in_section = 0
      printed = 0
    }
    index($0, target) == 1 {
      in_section = 1
    }
    in_section {
      if (printed && /^## \[/) {
        exit
      }
      print
      printed = 1
    }
  ' "$changelog_path"
)"

[[ -n "$section" ]] || fail "no changelog section found in $changelog_path for version $version"

printf '%s\n' "$section"
