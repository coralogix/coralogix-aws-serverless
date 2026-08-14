#!/usr/bin/env bash

# Run inside the AWS Lambda Node.js 24 base image with wrapper.zip extracted
# at /opt. This exercises the deployed exec wrapper against the SDK bundled
# in the runtime image, without contacting AWS.

set -euo pipefail

[[ "$(node -p 'process.versions.node.split(".")[0]')" == "24" ]] || {
  echo "secretlayer_node24_smoke: Node.js 24 is required" >&2
  exit 1
}
[[ -x /opt/wrapper.sh ]] || {
  echo "secretlayer_node24_smoke: /opt/wrapper.sh is not executable" >&2
  exit 1
}

export NODE_PATH="${NODE_PATH:-/var/runtime/node_modules}"
sdk_path="$(node -p 'require.resolve("@aws-sdk/client-secrets-manager")')"
case "$sdk_path" in
  /var/runtime/node_modules/*) ;;
  *)
    echo "secretlayer_node24_smoke: SDK did not load from the Lambda runtime: $sdk_path" >&2
    exit 1
    ;;
esac

work="$(mktemp -d)"
server_pid=""
cleanup() {
  [[ -z "$server_pid" ]] || kill "$server_pid" 2>/dev/null || true
  rm -rf "$work"
  rm -f /tmp/envVars
}
trap cleanup EXIT

cat > "$work/secrets-server.js" <<'EOF'
const fs = require("fs");
const http = require("http");

const server = http.createServer((_request, response) => {
  response.writeHead(200, {
    "content-type": "application/x-amz-json-1.1",
    "x-amzn-requestid": "secretlayer-node24-smoke",
  });
  response.end(JSON.stringify({ SecretString: "node24-smoke-secret" }));
});

server.listen(0, "127.0.0.1", () => {
  fs.writeFileSync(process.env.PORT_FILE, String(server.address().port));
});
EOF

PORT_FILE="$work/port" node "$work/secrets-server.js" &
server_pid=$!
for _ in {1..100}; do
  [[ -s "$work/port" ]] && break
  kill -0 "$server_pid" 2>/dev/null || {
    echo "secretlayer_node24_smoke: mock Secrets Manager stopped" >&2
    exit 1
  }
  sleep 0.05
done
[[ -s "$work/port" ]] || {
  echo "secretlayer_node24_smoke: mock Secrets Manager did not start" >&2
  exit 1
}

rm -f /tmp/envVars
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
export AWS_LAMBDA_FUNCTION_NAME=secretlayer-smoke
export AWS_ENDPOINT_URL_SECRETS_MANAGER="http://127.0.0.1:$(<"$work/port")"

/opt/wrapper.sh /bin/bash -c \
  '[[ "$private_key" == "node24-smoke-secret" ]]'

[[ "$(< /tmp/envVars)" == "export private_key=node24-smoke-secret" ]] || {
  echo "secretlayer_node24_smoke: /tmp/envVars has unexpected content" >&2
  exit 1
}

printf 'secretlayer_node24_smoke: Node 24 loaded %s and populated /tmp/envVars\n' "$sdk_path"
