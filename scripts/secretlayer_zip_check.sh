#!/usr/bin/env bash

# src/lambda-secretLayer/wrapper.zip is a committed binary and is what the layer
# actually deploys (ContentUri in template.yaml). Nothing rebuilds it, so edits to
# the tracked wrapper sources ship only if someone re-zips by hand. This check
# fails when the two have drifted.
#
# Rebuild with: scripts/secretlayer_zip_build.sh

set -euo pipefail

layer_dir="${1:-src/lambda-secretLayer}"
zip_path="$layer_dir/wrapper.zip"
expected_entries="wrapper.sh wrapper16.js wrapper18.js"
# wrapper.sh is exec'd via AWS_LAMBDA_EXEC_WRAPPER=/opt/wrapper.sh, so it has to
# carry the execute bit inside the archive or the function dies with exit 126
expected_mode_wrapper_sh="-rwxr-xr-x"
expected_mode_default="-rw-r--r--"

fail() {
  echo "secretlayer_zip_check: $*" >&2
  exit 1
}

[[ -f "$zip_path" ]] || fail "missing $zip_path"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

unzip -q "$zip_path" -d "$work" || fail "could not unzip $zip_path"

# the archive must hold exactly the tracked wrapper files, nothing more
actual_entries="$(cd "$work" && find . -type f | sed 's|^\./||' | sort | tr '\n' ' ' | sed 's/ $//')"
sorted_expected="$(printf '%s\n' $expected_entries | sort | tr '\n' ' ' | sed 's/ $//')"
if [[ "$actual_entries" != "$sorted_expected" ]]; then
  fail "$zip_path contains [$actual_entries], expected [$sorted_expected]"
fi

drifted=0

# entry modes, read out of the archive rather than the extracted copies, since
# unzip can apply the umask on extraction
for entry in $expected_entries; do
  case "$entry" in
    wrapper.sh) want="$expected_mode_wrapper_sh" ;;
    *)          want="$expected_mode_default" ;;
  esac
  got="$(unzip -Z -l "$zip_path" | awk -v e="$entry" '$NF == e { print $1 }')"
  if [[ "$got" != "$want" ]]; then
    echo "secretlayer_zip_check: $entry has mode $got in wrapper.zip, expected $want" >&2
    if [[ "$entry" == "wrapper.sh" ]]; then
      echo "  wrapper.sh is exec'd via AWS_LAMBDA_EXEC_WRAPPER; without the execute bit the function fails with exit 126" >&2
    fi
    drifted=1
  fi
done

for entry in $expected_entries; do
  source_file="$layer_dir/$entry"
  [[ -f "$source_file" ]] || fail "missing tracked source $source_file"
  if ! diff -u "$source_file" "$work/$entry" >/dev/null; then
    echo "secretlayer_zip_check: $entry in wrapper.zip differs from $source_file" >&2
    diff -u "$source_file" "$work/$entry" | sed 's/^/  /' >&2 || true
    drifted=1
  fi
done

if [[ "$drifted" -ne 0 ]]; then
  fail "wrapper.zip is stale; rebuild it with scripts/secretlayer_zip_build.sh and commit the result"
fi

printf 'secretlayer_zip_check: wrapper.zip matches its tracked sources (%s)\n' "$expected_entries"
