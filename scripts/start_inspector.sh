#!/usr/bin/env bash
# ============================================================================
# Start MCP Inspector as a sidecar service for MACAE
# ============================================================================
#
# The Inspector provides:
#   - Visual UI for testing/debugging MCP servers (port 16274)
#   - Proxy server for multi-transport bridging (port 16277)
#
# The Inspector binds to [::1] (IPv6 only). In a Dev Container, VS Code
# port-forwarding needs IPv4. This script starts socat bridges automatically:
#   IPv4 0.0.0.0:16274 → IPv6 [::1]:16274  (UI)
#   IPv4 0.0.0.0:16277 → IPv6 [::1]:16277  (Proxy)
#
# Pre-configured to connect to the MACAE MCP server at localhost:9000
#
# Usage:
#   ./scripts/start_inspector.sh              # Start with defaults
#   ./scripts/start_inspector.sh --no-auth    # Start without auth (dev)
#   ./scripts/start_inspector.sh --background # Start in background
#   ./scripts/start_inspector.sh --force      # Kill existing and restart
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/src/mcp_server/mcp-inspector-config.json"
# Ports
CLIENT_PORT="${MCP_INSPECTOR_CLIENT_PORT:-16274}"
SERVER_PORT="${MCP_INSPECTOR_SERVER_PORT:-16277}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Cleanup handler ─────────────────────────────────────────────────────
SOCAT_PIDS=()
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down Inspector & socat bridges...${NC}"
    for pid in "${SOCAT_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    # Kill Inspector if still running
    [ -f "$PROJECT_ROOT/.inspector.pid" ] && kill "$(cat "$PROJECT_ROOT/.inspector.pid")" 2>/dev/null || true
    # Kill any remaining socat on our ports
    fuser -k "${CLIENT_PORT}/tcp" "${SERVER_PORT}/tcp" 2>/dev/null || true
    echo -e "${GREEN}✅ Cleaned up${NC}"
}
trap cleanup EXIT

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        MCP Inspector — MACAE Sidecar Service            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Node.js version
NODE_VERSION=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" -lt 22 ]; then
    echo -e "${YELLOW}⚠️  Node.js >= 22.7.5 required for MCP Inspector${NC}"
    echo "   Current: $(node --version 2>/dev/null || echo 'not installed')"
    echo "   Install: https://nodejs.org/"
    exit 1
fi

# Check socat
if ! command -v socat &>/dev/null; then
    echo -e "${YELLOW}⚠️  socat not found — installing...${NC}"
    sudo apt-get update -qq && sudo apt-get install -yqq socat
fi

# Check if Inspector config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠️  Config file not found: $CONFIG_FILE${NC}"
    echo "   Creating default config pointing to MACAE MCP server..."
    cat > "$CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "macae-mcp-server": {
      "type": "streamable-http",
      "url": "http://localhost:9000/mcp",
      "note": "MACAE internal MCP server"
    }
  }
}
EOF
fi

# Parse arguments
BACKGROUND=false
EXTRA_ARGS=""
for arg in "$@"; do
    case $arg in
        --background|-b)
            BACKGROUND=true
            ;;
        --no-auth)
            export DANGEROUSLY_OMIT_AUTH=true
            echo -e "${YELLOW}⚠️  Authentication disabled (--no-auth)${NC}"
            ;;
        --force|-f)
            FORCE=true
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $arg"
            ;;
    esac
done

# Prevent browser auto-open (crashes in devcontainer)
export CLIENT_PORT="$CLIENT_PORT"
export SERVER_PORT="$SERVER_PORT"
export MCP_AUTO_OPEN_ENABLED=false
export BROWSER=none

INSPECTOR_LOG="$PROJECT_ROOT/.inspector.log"
INSPECTOR_PID_FILE="$PROJECT_ROOT/.inspector.pid"

# ── Single-instance guard ────────────────────────────────────────────────
if [ -f "$INSPECTOR_PID_FILE" ]; then
    OLD_PID=$(cat "$INSPECTOR_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Inspector already running (PID: $OLD_PID)${NC}"
        TOKEN=$(grep -oP 'MCP_PROXY_AUTH_TOKEN=\K[a-f0-9]+' "$INSPECTOR_LOG" 2>/dev/null | tail -1)
        if [ -n "$TOKEN" ]; then
            echo -e "${GREEN}🌐 Open in browser:${NC}"
            echo "   http://localhost:${CLIENT_PORT}/?MCP_PROXY_AUTH_TOKEN=${TOKEN}&MCP_PROXY_PORT=${SERVER_PORT}"
        fi
        echo -e "${BLUE}   Use --force to restart, or kill $OLD_PID to stop.${NC}"
        if [ "$FORCE" != true ]; then
            exit 0
        fi
        echo -e "${YELLOW}   --force: killing existing instance...${NC}"
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$INSPECTOR_PID_FILE"
fi

# ── Kill anything on our ports ───────────────────────────────────────────
fuser -k "${CLIENT_PORT}/tcp" "${SERVER_PORT}/tcp" 2>/dev/null || true
sleep 1

# ── Rotate log (keep previous run for debugging) ─────────────────────────
if [ -f "$INSPECTOR_LOG" ]; then
    mv "$INSPECTOR_LOG" "${INSPECTOR_LOG}.prev" 2>/dev/null || true
fi

echo -e "${GREEN}📋 Configuration:${NC}"
echo "   Inspector UI:    http://localhost:${CLIENT_PORT}"
echo "   Proxy Server:    http://localhost:${SERVER_PORT}"
echo "   Config File:     $CONFIG_FILE"
echo "   MACAE MCP:       http://localhost:9000/mcp"
echo "   Log File:        $INSPECTOR_LOG"
echo ""

# ── Start Inspector in background, then add socat bridges ────────────────
echo -e "${GREEN}🚀 Starting Inspector...${NC}"

# Always run Inspector as a background process so we can add socat
echo "--- Inspector started: $(date -Iseconds) ---" >> "$INSPECTOR_LOG"
nohup npx @modelcontextprotocol/inspector \
    --config "$CONFIG_FILE" \
    --server macae-mcp-server \
    $EXTRA_ARGS \
    >> "$INSPECTOR_LOG" 2>&1 &
INSPECTOR_PID=$!
echo "$INSPECTOR_PID" > "$INSPECTOR_PID_FILE"

# Wait for Inspector to bind its IPv6 ports
echo -e "${BLUE}   Waiting for Inspector to start...${NC}"
for i in $(seq 1 15); do
    if ss -tlnp 2>/dev/null | grep -q ":${CLIENT_PORT}" && \
       ss -tlnp 2>/dev/null | grep -q ":${SERVER_PORT}"; then
        break
    fi
    sleep 1
done

# Verify Inspector is listening
if ! ss -tlnp 2>/dev/null | grep -q ":${CLIENT_PORT}"; then
    echo -e "${RED}❌ Inspector failed to start. Log:${NC}"
    cat "$INSPECTOR_LOG"
    exit 1
fi

# Extract token from log
TOKEN=$(grep -oP 'MCP_PROXY_AUTH_TOKEN=\K[a-f0-9]+' "$INSPECTOR_LOG" 2>/dev/null | tail -1)

echo -e "${GREEN}✅ Inspector running (PID: $INSPECTOR_PID)${NC}"

# ── Start socat IPv4→IPv6 bridges ────────────────────────────────────────
# The Inspector binds to [::1] (IPv6 only). VS Code Dev Container port
# forwarding needs 0.0.0.0 (IPv4). socat bridges the gap.

echo -e "${BLUE}🔌 Starting IPv4→IPv6 socat bridges...${NC}"

# Bridge for UI port
socat TCP4-LISTEN:${CLIENT_PORT},bind=0.0.0.0,fork,reuseaddr TCP6:[::1]:${CLIENT_PORT} &
SOCAT_PIDS+=($!)

# Bridge for Proxy port
socat TCP4-LISTEN:${SERVER_PORT},bind=0.0.0.0,fork,reuseaddr TCP6:[::1]:${SERVER_PORT} &
SOCAT_PIDS+=($!)

sleep 1

# Verify bridges
if ss -tlnp 2>/dev/null | grep "0.0.0.0:${CLIENT_PORT}" >/dev/null; then
    echo -e "${GREEN}✅ IPv4 bridge: 0.0.0.0:${CLIENT_PORT} → [::1]:${CLIENT_PORT}${NC}"
else
    echo -e "${YELLOW}⚠️  UI bridge may not have started (port ${CLIENT_PORT})${NC}"
fi

if ss -tlnp 2>/dev/null | grep "0.0.0.0:${SERVER_PORT}" >/dev/null; then
    echo -e "${GREEN}✅ IPv4 bridge: 0.0.0.0:${SERVER_PORT} → [::1]:${SERVER_PORT}${NC}"
else
    echo -e "${YELLOW}⚠️  Proxy bridge may not have started (port ${SERVER_PORT})${NC}"
fi

echo ""
if [ -n "$TOKEN" ]; then
    UI_URL="http://localhost:${CLIENT_PORT}/?MCP_PROXY_AUTH_TOKEN=${TOKEN}&MCP_PROXY_PORT=${SERVER_PORT}"
    echo -e "${GREEN}🔑 Token: ${TOKEN:0:20}...${NC}"
else
    UI_URL="http://localhost:${CLIENT_PORT}/?MCP_PROXY_PORT=${SERVER_PORT}"
fi
echo -e "${GREEN}🌐 Open in browser:${NC}"
echo -e "   ${UI_URL}"
echo ""
echo -e "${BLUE}   Press Ctrl+C to stop${NC}"

# ── Wait for Inspector to exit ───────────────────────────────────────────
if [ "$BACKGROUND" = true ]; then
    echo ""
    echo -e "${GREEN}✅ Running in background${NC}"
    echo "   Logs: $INSPECTOR_LOG"
    echo "   Stop: kill \$(cat $INSPECTOR_PID_FILE)"
else
    # Tail the log and wait for Inspector to die
    tail -n 0 -f "$INSPECTOR_LOG" &
    TAIL_PID=$!
    wait $INSPECTOR_PID 2>/dev/null
    kill $TAIL_PID 2>/dev/null
fi
