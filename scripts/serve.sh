#!/usr/bin/env bash
# Run the OCR API + MCP (streamable HTTP) as long-lived background services,
# optionally exposed through Cloudflare quick tunnels.
#
# Usage: scripts/serve.sh {start|stop|restart|status|urls}
#
# Env overrides: OCR_API_PORT (8000), MCP_PORT (8001), OCR_SERVE_TUNNEL (default 0; 1 = start
# cloudflared quick tunnels), CLOUDFLARED_BIN, OCR_SERVE_DIR (.server).
# The shared bearer token lives in .server-token (generated on first start, chmod 600)
# and is used as OCR_ENGINE_API_KEY (API) and MCP_AUTH_TOKEN (MCP). Provider keys
# (OPENROUTER_API_KEY, DOCSTRANGE_API_KEY, ...) come from the environment or .env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STATE_DIR="${OCR_SERVE_DIR:-$ROOT/.server}"
LOG_DIR="$STATE_DIR/logs"
PID_DIR="$STATE_DIR/pids"
TOKEN_FILE="$ROOT/.server-token"
API_PORT="${OCR_API_PORT:-8000}"
MCP_PORT="${MCP_PORT:-8001}"
TUNNEL="${OCR_SERVE_TUNNEL:-0}"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-$(command -v cloudflared || echo "$HOME/.local/bin/cloudflared")}"
SERVICES=(api mcp)
if [[ "$TUNNEL" == "1" ]]; then SERVICES+=(tunnel-api tunnel-mcp); fi

mkdir -p "$LOG_DIR" "$PID_DIR"

ensure_token() {
  if [[ ! -s "$TOKEN_FILE" ]]; then
    (umask 077; python3 -c 'import secrets; print("ocrsrv_" + secrets.token_urlsafe(32))' >"$TOKEN_FILE")
  fi
  chmod 600 "$TOKEN_FILE"
}

service_cmd() {
  case "$1" in
    api) echo "exec uv run --frozen ocr-api" ;;
    mcp) echo "exec uv run --frozen ocr-mcp" ;;
    tunnel-api) echo "exec '$CLOUDFLARED_BIN' tunnel --no-autoupdate --url http://127.0.0.1:$API_PORT" ;;
    tunnel-mcp) echo "exec '$CLOUDFLARED_BIN' tunnel --no-autoupdate --url http://127.0.0.1:$MCP_PORT" ;;
  esac
}

is_running() {
  local pidfile="$PID_DIR/$1.pid"
  [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null
}

start_service() {
  local name="$1"
  if is_running "$name"; then echo "$name already running (pid $(cat "$PID_DIR/$name.pid"))"; return; fi
  local token; token="$(cat "$TOKEN_FILE")"
  # Supervisor loop: restart the child if it exits, until the supervisor is killed.
  OCR_ENV=production \
  OCR_ENGINE_API_KEY="$token" \
  OCR_RUNS_DIR="${OCR_RUNS_DIR:-$ROOT/runs}" \
  OCR_API_HOST=127.0.0.1 OCR_API_PORT="$API_PORT" \
  OCR_API_BASE_URL="http://127.0.0.1:$API_PORT" OCR_API_KEY="$token" \
  MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT="$MCP_PORT" MCP_AUTH_TOKEN="$token" \
  nohup setsid bash -c "
    trap 'kill 0' TERM INT
    while true; do
      echo \"[\$(date -Is)] starting $name\"
      bash -c \"$(service_cmd "$name")\" &
      wait \$!
      echo \"[\$(date -Is)] $name exited (\$?), restarting in 3s\"
      sleep 3
    done" >>"$LOG_DIR/$name.log" 2>&1 < /dev/null &
  echo $! >"$PID_DIR/$name.pid"
  echo "started $name (supervisor pid $!) -> $LOG_DIR/$name.log"
}

stop_service() {
  local name="$1" pidfile="$PID_DIR/$1.pid"
  if is_running "$name"; then
    local pid; pid="$(cat "$pidfile")"
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    echo "stopped $name (pid $pid)"
  fi
  rm -f "$pidfile"
}

print_urls() {
  for t in api mcp; do
    local log="$LOG_DIR/tunnel-$t.log" url=""
    [[ -f "$log" ]] && url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$log" | tail -1 || true)"
    if [[ -n "$url" ]]; then
      [[ "$t" == "mcp" ]] && url="$url/mcp"
      echo "$t: $url"
    fi
  done | tee "$STATE_DIR/public-urls.txt"
}

case "${1:-status}" in
  start)
    ensure_token
    for s in "${SERVICES[@]}"; do start_service "$s"; done
    if [[ "$TUNNEL" == "1" ]]; then sleep 8; print_urls; fi
    ;;
  stop) for s in "${SERVICES[@]}"; do stop_service "$s"; done ;;
  restart) "$0" stop; sleep 2; "$0" start ;;
  status)
    for s in "${SERVICES[@]}"; do
      if is_running "$s"; then echo "$s: running (pid $(cat "$PID_DIR/$s.pid"))"; else echo "$s: stopped"; fi
    done
    ;;
  urls) print_urls ;;
  *) echo "usage: $0 {start|stop|restart|status|urls}" >&2; exit 2 ;;
esac
