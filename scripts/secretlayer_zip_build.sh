#!/usr/bin/env bash

# Rebuild src/lambda-secretLayer/wrapper.zip from the tracked wrapper sources.
#
# wrapper.sh must be executable in the archive: consumers set
# AWS_LAMBDA_EXEC_WRAPPER=/opt/wrapper.sh (see src/resource-metadata-sqs/template.yaml)
# and Lambda execs that path, so a non-executable entry fails with exit 126 before
# the handler starts. The wrappers it dispatches to are only ever passed to node,
# so they stay non-executable.
#
# Deterministic on purpose: modes and mtimes are fixed, so rebuilding from
# unchanged sources produces a byte-identical archive and the committed binary
# does not churn.

set -euo pipefail

layer_dir="${1:-src/lambda-secretLayer}"
zip_name="wrapper.zip"
entries="wrapper18.js wrapper16.js wrapper.sh"
executable_entries=" wrapper.sh "
# fixed so rebuilds are reproducible; matches when the sources last changed (#190)
mtime="202606110000"

command -v zip >/dev/null || { echo "secretlayer_zip_build: zip is not installed" >&2; exit 1; }

layer_dir="$(cd "$layer_dir" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

for entry in $entries; do
  [[ -f "$layer_dir/$entry" ]] || { echo "secretlayer_zip_build: missing $layer_dir/$entry" >&2; exit 1; }
  cp "$layer_dir/$entry" "$work/$entry"
  case "$executable_entries" in
    *" $entry "*) chmod 755 "$work/$entry" ;;
    *)            chmod 644 "$work/$entry" ;;
  esac
  touch -t "$mtime" "$work/$entry"
done

# -X drops extra file attributes (uid/gid, extended timestamps) that would
# otherwise vary per machine and make the committed binary churn
(cd "$work" && zip -q -X "$zip_name" $entries)

mv "$work/$zip_name" "$layer_dir/$zip_name"
printf 'secretlayer_zip_build: wrote %s/%s\n' "$layer_dir" "$zip_name"
