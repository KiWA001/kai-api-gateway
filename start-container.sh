#!/usr/bin/env sh
set -eu

: "${PORT:=7860}"
: "${KAI_CLI_PROXY_ENABLED:=true}"
: "${KAI_CLI_PROXY_URL:=http://127.0.0.1:8317}"
: "${KAI_CLI_PROXY_API_KEY:=sk-kai-cli-proxy}"
: "${KAI_CLI_PROXY_MANAGEMENT_KEY:=sk-kai-cli-management}"
: "${KAI_CLI_PROXY_CONFIG_PATH:=/tmp/cliproxy/config.yaml}"
: "${KAI_CLI_PROXY_AUTH_DIR:=/tmp/cliproxy/auths}"

cliproxy_pid=""

if [ "$KAI_CLI_PROXY_ENABLED" = "true" ] || [ "$KAI_CLI_PROXY_ENABLED" = "1" ]; then
  mkdir -p "$(dirname "$KAI_CLI_PROXY_CONFIG_PATH")" "$KAI_CLI_PROXY_AUTH_DIR"

  cat > "$KAI_CLI_PROXY_CONFIG_PATH" <<EOF
host: "127.0.0.1"
port: 8317
auth-dir: "$KAI_CLI_PROXY_AUTH_DIR"
api-keys:
  - "$KAI_CLI_PROXY_API_KEY"
remote-management:
  allow-remote: false
  secret-key: ""
  disable-control-panel: true
debug: false
logging-to-file: false
usage-statistics-enabled: false
ws-auth: true
request-retry: 3
max-retry-credentials: 0
max-retry-interval: 30
disable-cooling: false
quota-exceeded:
  switch-project: true
  switch-preview-model: true
  antigravity-credits: true
routing:
  strategy: "round-robin"
  session-affinity: false
EOF

  export MANAGEMENT_PASSWORD="$KAI_CLI_PROXY_MANAGEMENT_KEY"
  /usr/local/bin/CLIProxyAPI -config "$KAI_CLI_PROXY_CONFIG_PATH" -local-model > /tmp/cliproxy/cliproxy.log 2>&1 &
  cliproxy_pid="$!"
fi

cleanup() {
  if [ -n "$cliproxy_pid" ]; then
    kill "$cliproxy_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
