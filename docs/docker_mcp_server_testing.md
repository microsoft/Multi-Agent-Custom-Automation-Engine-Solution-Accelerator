# Docker MCP Server Testing Guide

This document provides comprehensive steps to test the MACAE MCP Server deployed in a Docker container.

## Prerequisites

- Docker installed and running
- Git repository cloned locally
- Basic understanding of MCP (Model Context Protocol)
- curl or similar HTTP client tool

## Quick Start

```bash
# Navigate to MCP server directory
cd src/backend/v3/mcp_server

# Build and run in one command
docker build -t macae-mcp-server . && docker run -d --name macae-mcp-server -p 9000:9000 macae-mcp-server python mcp_server.py --transport http --host 0.0.0.0 --port 9000
```

## Step-by-Step Testing Process

### 1. Build the Docker Image

```bash
# Navigate to the MCP server directory
cd c:\workstation\Microsoft\github\MACAE_ME\src\backend\v3\mcp_server

# Build the Docker image
docker build -t macae-mcp-server:latest .
```

**Expected Output:**

```
Successfully built [image-id]
Successfully tagged macae-mcp-server:latest
```

### 2. Run the Container

```bash
# Run with HTTP transport for testing
docker run -d \
  --name macae-mcp-server \
  -p 9000:9000 \
  -e MCP_DEBUG=true \
  macae-mcp-server:latest \
  python mcp_server.py --transport http --host 0.0.0.0 --port 9000 --debug
```

### 3. Verify Container is Running

```bash
# Check container status
docker ps

# View container logs
docker logs macae-mcp-server
```

**Expected Log Output:**

```
🚀 Starting MACAE MCP Server
📋 Transport: HTTP
🔧 Debug: True
🔐 Auth: Disabled
🌐 Host: 0.0.0.0
🌐 Port: 9000
--------------------------------------------------
🚀 MACAE MCP Server initialized
📊 Total services: 3
🔧 Total tools: [number]
🔐 Authentication: Disabled
   📁 hr: [count] tools (HRService)
   📁 tech_support: [count] tools (TechSupportService)
   📁 general: [count] tools (GeneralService)
🤖 Starting FastMCP server with http transport
🌐 Server will be available at: http://0.0.0.0:9000/mcp/
```

## Testing Methods

### Method 1: Health Check Testing

```bash
# Test if the server is responding
curl -i http://localhost:9000/health

# Expected response
HTTP/1.1 200 OK
Content-Type: application/json
{"status": "healthy", "timestamp": "2025-08-11T..."}
```

### Method 2: MCP Endpoint Testing

```bash
# Test MCP endpoint availability
curl -i http://localhost:9000/mcp/

# Check MCP capabilities
curl -X POST http://localhost:9000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}'
```

### Method 3: Tool Discovery Testing

```bash
# List available tools
curl -X POST http://localhost:9000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'
```

**Expected Response Structure:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "hr_get_employee_info",
        "description": "Get employee information",
        "inputSchema": { ... }
      },
      ...
    ]
  }
}
```

### Method 4: Tool Execution Testing

```bash
# Test a specific tool (example: HR service)
curl -X POST http://localhost:9000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "hr_get_employee_info",
      "arguments": {
        "employee_id": "12345"
      }
    }
  }'
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Container Won't Start

```bash
# Check Docker logs for errors
docker logs macae-mcp-server

# Common solutions:
# - Ensure port 9000 is not in use
# - Check if all dependencies are installed in the image
# - Verify the Python path is correct
```

#### 2. Port Already in Use

```bash
# Find what's using port 9000
netstat -ano | findstr :9000

# Use a different port
docker run -d --name macae-mcp-server -p 9001:9000 macae-mcp-server python mcp_server.py --transport http --host 0.0.0.0 --port 9000
```

#### 3. Connection Refused

```bash
# Ensure container is listening on all interfaces
docker exec macae-mcp-server netstat -tlnp

# Check if firewall is blocking the connection
# Restart container with correct host binding
docker stop macae-mcp-server
docker rm macae-mcp-server
# Re-run with --host 0.0.0.0
```

#### 4. Authentication Issues

```bash
# Disable auth for testing
docker run -d \
  --name macae-mcp-server \
  -p 9000:9000 \
  -e MCP_ENABLE_AUTH=false \
  macae-mcp-server python mcp_server.py --transport http --host 0.0.0.0 --port 9000 --no-auth
```

## Performance Testing

### Load Testing with curl

```bash
# Simple load test
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9000/health &
done
wait
```

### Memory and CPU Monitoring

```bash
# Monitor container resources
docker stats macae-mcp-server

# Get detailed container info
docker inspect macae-mcp-server
```

## Integration Testing

### Test with MCP Client

```python
# Python client test example
import asyncio
import httpx
import json

async def test_mcp_client():
    async with httpx.AsyncClient() as client:
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        response = await client.post(
            "http://localhost:9000/mcp/",
            json=init_request
        )
        print("Initialize response:", response.json())

        # List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = await client.post(
            "http://localhost:9000/mcp/",
            json=tools_request
        )
        print("Tools response:", response.json())

# Run the test
asyncio.run(test_mcp_client())
```

## Clean Up

```bash
# Stop and remove container
docker stop macae-mcp-server
docker rm macae-mcp-server

# Remove image (optional)
docker rmi macae-mcp-server:latest

# Clean up unused Docker resources
docker system prune -f
```

## Environment Configurations

### Development Environment

```bash
docker run -d \
  --name macae-mcp-server-dev \
  -p 9000:9000 \
  -e MCP_DEBUG=true \
  -e MCP_ENABLE_AUTH=false \
  -v $(pwd)/config:/app/config:ro \
  macae-mcp-server python mcp_server.py --transport http --host 0.0.0.0 --port 9000 --debug
```

### Production Environment

```bash
docker run -d \
  --name macae-mcp-server-prod \
  -p 9000:9000 \
  -e MCP_DEBUG=false \
  -e MCP_ENABLE_AUTH=true \
  -e MCP_JWKS_URI="https://your-auth-provider/.well-known/jwks.json" \
  -e MCP_ISSUER="https://your-auth-provider/" \
  -e MCP_AUDIENCE="your-audience" \
  --restart unless-stopped \
  macae-mcp-server python mcp_server.py --transport http --host 0.0.0.0 --port 9000
```

## Docker Compose Testing

Create `docker-compose.test.yml`:

```yaml
version: "3.8"

services:
  mcp-server:
    build: .
    ports:
      - "9000:9000"
    environment:
      - MCP_DEBUG=true
      - MCP_ENABLE_AUTH=false
    command: python mcp_server.py --transport http --host 0.0.0.0 --port 9000 --debug
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s

  test-runner:
    image: curlimages/curl:latest
    depends_on:
      mcp-server:
        condition: service_healthy
    command: |
      sh -c "
        echo 'Testing MCP Server...'
        curl -f http://mcp-server:9000/health || exit 1
        echo 'Health check passed!'
        curl -X POST http://mcp-server:9000/mcp/ -H 'Content-Type: application/json' -d '{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"tools/list\", \"params\": {}}' || exit 1
        echo 'Tools list test passed!'
        echo 'All tests completed successfully!'
      "
```

Run tests:

```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Success Criteria

✅ Container builds without errors  
✅ Container starts and shows initialization logs  
✅ Health endpoint returns 200 OK  
✅ MCP endpoint accepts JSON-RPC requests  
✅ Tools can be listed via API  
✅ Tools can be executed via API  
✅ Container handles graceful shutdown  
✅ No memory leaks during extended operation

## Next Steps

1. **Security Testing**: Test with authentication enabled
2. **Stress Testing**: Use tools like Apache Bench or wrk
3. **Integration Testing**: Test with actual MCP clients
4. **Monitoring Setup**: Add logging and metrics collection
5. **Deployment**: Deploy to production environment (Azure Container Instances, Kubernetes, etc.)

## Useful Commands Reference

```bash
# Quick container restart
docker restart macae-mcp-server

# Execute commands inside container
docker exec -it macae-mcp-server /bin/bash

# Copy files from container
docker cp macae-mcp-server:/app/logs ./container-logs

# View real-time logs
docker logs -f macae-mcp-server

# Check container health
docker inspect --format='{{.State.Health.Status}}' macae-mcp-server
```

---

For additional help and troubleshooting, refer to the main [DeploymentGuide.md](./DeploymentGuide.md) and [LocalDeployment.md](./LocalDeployment.md) documentation.
