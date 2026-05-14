"""Quick test to list MCP tools on /hr/mcp."""
import json

import httpx

BASE = "http://127.0.0.1:9000/hr/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# 1. Initialize
r = httpx.post(
    BASE,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
    },
    headers=HEADERS,
)
print("Init status:", r.status_code)
print("Init body:", r.text[:500])
sid = r.headers.get("mcp-session-id", "")
print("Session ID:", sid[:40] if sid else "NONE")

if not sid:
    print("No session ID, aborting")
    exit(1)

# 2. List tools
HEADERS["mcp-session-id"] = sid
r2 = httpx.post(
    BASE,
    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    headers=HEADERS,
)
print("\nTools status:", r2.status_code)
body = r2.text
print("Raw response (first 300):", body[:300])

# Try to parse SSE or JSON
for line in body.splitlines():
    if line.startswith("data:"):
        payload = line[len("data:"):].strip()
        if payload:
            data = json.loads(payload)
            tools = data.get("result", {}).get("tools", [])
            print(f"\n{len(tools)} tools found:")
            for t in tools:
                print(f"  - {t['name']}")
            break
else:
    # Maybe it's plain JSON
    try:
        data = json.loads(body)
        tools = data.get("result", {}).get("tools", [])
        print(f"\n{len(tools)} tools found:")
        for t in tools:
            print(f"  - {t['name']}")
    except json.JSONDecodeError:
        print("Could not parse response")
