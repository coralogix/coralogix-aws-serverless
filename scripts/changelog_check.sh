#!/usr/bin/env bash

set -euo pipefail

package_dir="${1:-}"
base_ref="${2:-origin/master}"

fail() {
  echo "changelog_check: $*" >&2
  exit 1
}

extract_semver_from_stream() {
  sed -n 's/^[[:space:]]*SemanticVersion:[[:space:]]*//p' \
    | head -n1 \
    | tr -d '"\r' \
    | xargs
}

semver_gt() {
  local left="$1"
  local right="$2"

  [[ "$left" != "$right" ]] && [[ "$(printf '%s\n%s\n' "$right" "$left" | sort -V | tail -n1)" == "$left" ]]
}

top_section_has_bullet() {
  local changelog_path="$1"

  awk '
    BEGIN { in_top_section = 0; found_bullet = 0 }
    /^## \[/ {
      if (in_top_section) {
        exit
      }
      in_top_section = 1
      next
    }
    in_top_section && /^[[:space:]]*-[[:space:]]/ {
      found_bullet = 1
    }
    END {
      exit(found_bullet ? 0 : 1)
    }
  ' "$changelog_path"
}

if [[ -z "$package_dir" ]]; then
  fail "usage: scripts/changelog_check.sh <src/package-dir> [base-ref]"
fi

package_dir="${package_dir#./}"
package_dir="${package_dir%/}"
template_path="$package_dir/template.yaml"
changelog_path="$package_dir/CHANGELOG.md"

[[ -f "$template_path" ]] || fail "missing template file: $template_path"
[[ -f "$changelog_path" ]] || fail "missing changelog file: $changelog_path"

git rev-parse --verify "$base_ref" >/dev/null 2>&1 || fail "base ref not found: $base_ref"

current_semver="$(extract_semver_from_stream < "$template_path")"
[[ -n "$current_semver" ]] || fail "could not read SemanticVersion from $template_path"

top_header="$(awk '/^## / { print; exit }' "$changelog_path")"
[[ -n "$top_header" ]] || fail "missing release heading in $changelog_path"
[[ "$top_header" =~ ^##\ \[[0-9]+\.[0-9]+\.[0-9]+\]\ -\ [0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] \
  || fail "top changelog entry in $changelog_path must look like: ## [X.Y.Z] - YYYY-MM-DD"

top_semver="$(printf '%s\n' "$top_header" | sed -E 's/^## \[([^]]+)\] - .*/\1/')"
if [[ "$top_semver" != "$current_semver" ]]; then
  fail "top changelog version ($top_semver) does not match $template_path SemanticVersion ($current_semver)"
fi

top_section_has_bullet "$changelog_path" || fail "top changelog entry in $changelog_path must include at least one bullet"

base_template="$(git show "$base_ref:$template_path" 2>/dev/null || true)"
base_semver=""
if [[ -n "$base_template" ]]; then
  base_semver="$(printf '%s\n' "$base_template" | extract_semver_from_stream)"
fi

changed_files="$(git diff --name-only "$base_ref"... -- "$package_dir")"

has_non_changelog_changes=0
while IFS= read -r changed_file; do
  [[ -n "$changed_file" ]] || continue
  if [[ "$changed_file" != "$changelog_path" ]]; then
    has_non_changelog_changes=1
    break
  fi
done <<< "$changed_files"

if [[ "$has_non_changelog_changes" -eq 1 && -n "$base_semver" ]] && ! semver_gt "$current_semver" "$base_semver"; then
  printf 'changelog_check: package changes detected in %s without a SemanticVersion bump\n' "$package_dir" >&2
  printf 'changelog_check: base=%s current=%s\n' "$base_semver" "$current_semver" >&2
  printf 'changelog_check: changed files:\n' >&2
  printf '%s\n' "$changed_files" | sed 's/^/  /' >&2
  fail "bump $template_path SemanticVersion and keep the top $changelog_path entry in sync, or use the 'skip-changelog' label"
fi

printf 'changelog_check: %s passed\n' "$package_dir"
