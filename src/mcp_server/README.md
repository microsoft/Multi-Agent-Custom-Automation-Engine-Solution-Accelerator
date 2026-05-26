# MACAE MCP Server

A FastMCP-based Model Context Protocol (MCP) server for the Multi-Agent Custom Automation Engine (MACAE) solution accelerator.

## Features

- **FastMCP Server**: Pure FastMCP implementation supporting multiple transport protocols
- **Factory Pattern**: Reusable MCP tools factory for easy service management
- **Domain-Based Organization**: Services organized by business domains (HR, Tech Support, etc.)
- **Authentication**: Optional Azure AD authentication support
- **Multiple Transports**: STDIO, HTTP (Streamable), and SSE transport support
- **Docker Support**: Containerized deployment with health checks
- **VS Code Integration**: Debug configurations and development settings
- **Comprehensive Testing**: Unit tests with pytest
- **Flexible Configuration**: Environment-based configuration management

## Architecture

```text
src/backend/v4/mcp_server/
├── core/                   # Core factory and base classes
│   ├── __init__.py
│   └── factory.py         # MCPToolFactory and base classes
├── services/               # Domain-specific service implementations
│   ├── __init__.py
│   ├── hr_service.py      # Human Resources tools
│   ├── tech_support_service.py # IT/Tech Support tools
│   └── general_service.py # General purpose tools
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── date_utils.py      # Date formatting utilities
│   └── formatters.py      # Response formatting utilities
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py        # Settings and configuration
├── mcp_server.py          # FastMCP server implementation
├── requirements.txt       # Python dependencies
├── uv.lock               # Lock file for dependencies
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Development container setup
└── .vscode/              # VS Code configurations
    ├── launch.json       # Debug configurations
    └── settings.json     # Editor settings
```

## Available Services

### HR Service (Domain: hr)

- **schedule_orientation_session**: Schedule orientation for new employees
- **assign_mentor**: Assign mentors to new employees
- **register_for_benefits**: Register employees for benefits
- **provide_employee_handbook**: Provide employee handbook
- **initiate_background_check**: Start background verification
- **request_id_card**: Request employee ID cards
- **set_up_payroll**: Configure payroll for employees

### Tech Support Service (Domain: tech_support)

- **send_welcome_email**: Send welcome emails to new employees
- **set_up_office_365_account**: Create Office 365 accounts
- **configure_laptop**: Configure laptops for employees
- **setup_vpn_access**: Configure VPN access
- **create_system_accounts**: Create system accounts

### General Service (Domain: general)

- **greet**: Simple greeting function
- **get_server_status**: Retrieve server status information

## Quick Start

### Development Setup

1. **Clone and Navigate**:

   ```bash
   cd src/backend/v4/mcp_server
   ```

2. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the Server**:

   ```bash
   # Default STDIO transport (for local MCP clients)
   python mcp_server.py

   # HTTP transport with per-domain routing (recommended for local development)
   python mcp_server.py -t streamable-http --port 9000 --no-auth

   # HTTP transport bound to all interfaces (for Docker/remote access)
   python mcp_server.py -t streamable-http --host 0.0.0.0 --port 9000 --no-auth

   # Debug mode
   python mcp_server.py -t streamable-http --port 9000 --debug --no-auth
   ```

### Transport Options

#### 1. STDIO Transport (default)

- 🔧 Perfect for: Local tools, command-line integrations, Claude Desktop
- 🚀 Usage: `python mcp_server.py` or `python mcp_server.py --transport stdio`

#### 2. HTTP (Streamable) Transport

- 🌐 Perfect for: Web-based deployments, microservices, remote access
- 🚀 Usage: `python mcp_server.py --transport http --port 9000`
- 🌐 URL: `http://127.0.0.1:9000/mcp/`

#### 3. SSE Transport (deprecated)

- ⚠️ Legacy support only - use HTTP transport for new projects
- 🚀 Usage: `python mcp_server.py --transport sse --port 9000`

### FastMCP CLI Usage (Legacy — catch-all only)

> **Note:** `fastmcp run` bypasses `create_app()` and only exposes the catch-all
> `/mcp` endpoint with all tools. It does NOT enable per-domain routing.
> Use `python mcp_server.py` for the full per-domain architecture.

```bash
# Legacy: all tools on /mcp (no domain routing)
fastmcp run mcp_server.py -t streamable-http --port 9000 -l DEBUG

# Development mode with MCP Inspector (catch-all only)
fastmcp dev mcp_server.py -t streamable-http --port 9000
```

### Docker Deployment

1. **Build and Run**:

   ```bash
   docker-compose up --build
   ```

2. **Access the Server**:
   - MCP endpoint: <http://localhost:9000/mcp/>
   - Health check available via custom routes

### VS Code Development

1. **Open in VS Code**:

   ```bash
   code .
   ```

2. **Use Debug Configurations**:
   - `Debug MCP Server (STDIO)`: Run with STDIO transport
   - `Debug MCP Server (HTTP)`: Run with HTTP transport
   - `Debug Tests`: Run the test suite

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Server Settings
MCP_HOST=0.0.0.0
MCP_PORT=9000
MCP_DEBUG=false
MCP_SERVER_NAME=MACAE MCP Server

# Authentication Settings
MCP_ENABLE_AUTH=true
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_JWKS_URI=https://login.microsoftonline.com/your-tenant-id/discovery/v2.0/keys
AZURE_ISSUER=https://sts.windows.net/your-tenant-id/
AZURE_AUDIENCE=api://your-client-id
```

### Authentication

When `MCP_ENABLE_AUTH=true`, the server expects Azure AD Bearer tokens. Configure your Azure App Registration with the appropriate settings.

For development, set `MCP_ENABLE_AUTH=false` to disable authentication.

## Adding New Services

1. **Create Service Class**:

   ```python
   from core.factory import MCPToolBase, Domain

   class MyService(MCPToolBase):
       def __init__(self):
           super().__init__(Domain.MY_DOMAIN)

       def register_tools(self, mcp):
           @mcp.tool(tags={self.domain.value})
           async def my_tool(param: str) -> str:
               # Tool implementation
               pass

       @property
       def tool_count(self) -> int:
           return 1  # Number of tools
   ```

2. **Register in Server**:

   ```python
   # In mcp_server.py (gets registered automatically from services/ directory)
   factory.register_service(MyService())
   ```

3. **Add Domain** (if new):

   ```python
   # In core/factory.py
   class Domain(Enum):
       # ... existing domains
       MY_DOMAIN = "my_domain"
   ```

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest src/tests/mcp_server/

# Run with coverage
pytest --cov=. src/tests/mcp_server/

# Run specific test file
pytest src/tests/mcp_server/test_hr_service.py -v
```

## MCP Client Usage

### Python Client

```python
from fastmcp import Client

# Connect to HTTP server
client = Client("http://localhost:9000")

async with client:
    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {[tool.name for tool in tools]}")

    # Call a tool
    result = await client.call_tool("greet", {"name": "World"})
    print(result)
```

### Command Line Testing

```bash
# Test the server is running
curl http://localhost:9000/mcp/

# With FastMCP CLI for testing
fastmcp dev mcp_server.py -t streamable-http --port 9000
```

## Quick Test

**Test STDIO Transport:**

```bash
# Start server in STDIO mode
python mcp_server.py --debug --no-auth

# Test with client_example.py
python client_example.py
```

**Test HTTP Transport:**

```bash
# Start HTTP server
python mcp_server.py --transport http --port 9000 --debug --no-auth

# Test with FastMCP client
python -c "
from fastmcp import Client
import asyncio
async def test():
    async with Client('http://localhost:9000') as client:
        result = await client.call_tool('greet', {'name': 'Test'})
        print(result)
asyncio.run(test())
"
```

**Start the server:**

```bash
# Start with per-domain routing
python mcp_server.py -t streamable-http --port 9000 --no-auth

# Endpoints:
#   http://127.0.0.1:9000/hr/mcp           -> HR tools only
#   http://127.0.0.1:9000/tech_support/mcp  -> Tech Support tools only
#   http://127.0.0.1:9000/marketing/mcp     -> Marketing tools only
#   http://127.0.0.1:9000/product/mcp       -> Product tools only
#   http://127.0.0.1:9000/image/mcp         -> Image tools only
#   http://127.0.0.1:9000/mcp              -> All tools (catch-all)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're in the correct directory and dependencies are installed
2. **Authentication Errors**: Check your Azure AD configuration and tokens
3. **Port Conflicts**: Change the port in configuration if 9000 is already in use
4. **Missing fastmcp**: Install with `pip install fastmcp`

### Debug Mode

Enable debug mode for detailed logging:

```bash
python mcp_server.py --debug --no-auth
```

Or set in environment:

```env
MCP_DEBUG=true
```

### Logs

Check container logs:

```bash
docker-compose logs mcp-server
```

## Server Arguments

```bash
usage: mcp_server.py [-h] [--transport {stdio,http,streamable-http,sse}]
                     [--host HOST] [--port PORT] [--debug] [--no-auth]

MACAE MCP Server

options:
  -h, --help            show this help message and exit
  --transport, -t       Transport protocol (default: stdio)
  --host HOST           Host to bind to for HTTP transport (default: 127.0.0.1)
  --port, -p PORT       Port to bind to for HTTP transport (default: 9000)
  --debug               Enable debug mode
  --no-auth             Disable authentication
```

## Contributing

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation for new features
4. Use the provided VS Code configurations for development

## License

This project is part of the MACAE Solution Accelerator and follows the same licensing terms.
