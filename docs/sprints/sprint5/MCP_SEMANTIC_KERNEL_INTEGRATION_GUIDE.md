# MCP + Semantic Kernel Integration Guide

**Date**: October 10, 2025  
**Status**: Documentation  
**Purpose**: Explain how MCP tools connect to UI through Semantic Kernel

---

## 🔄 Complete Data Flow

### 1. Frontend UI → Backend API → MCP Tools

```
User drags & drops CSV file
  ↓
ForecastDatasetPanel.tsx (handleDrop)
  ↓
DatasetService.uploadDataset(file)
  ↓
POST /v3/datasets/upload
  ↓
Backend stores file in data/datasets/
  ↓
MCP tools can access via list_finance_datasets, summarize_financial_dataset
```

### 2. User Chat → Agent → MCP Tools → Response

```
User types message in HomeInput.tsx
  ↓
WebSocket message to backend
  ↓
OrchestrationManager creates agent team
  ↓
MagenticAgentFactory.create_agent_from_config()
  ↓
Agent initialized with MCP plugin (if use_mcp: true)
  ↓
Agent calls MCP tools via Semantic Kernel
  ↓
Results stream back to frontend via WebSocket
```

---

## 📦 Key Components

### Frontend (React/TypeScript)

**Drag & Drop Components:**
- `src/frontend/src/components/content/ForecastDatasetPanel.tsx` - Basic dataset upload
- `src/frontend/src/components/content/EnhancedForecastDatasetPanel.tsx` - Multi-file upload
- `src/frontend/src/pages/AnalyticsDashboard.tsx` - Analytics dashboard with KPIs

**Data Flow:**
```typescript
// 1. User drags file
handleDrop(event: React.DragEvent<HTMLDivElement>)
  ↓
// 2. Upload via service
await DatasetService.uploadDataset(file)
  ↓
// 3. Backend API call
POST /v3/datasets/upload
```

**Services:**
- `src/frontend/src/services/DatasetService.tsx` - API client for datasets
- `src/frontend/src/api/apiClient.ts` - HTTP client wrapper

### Backend (Python/FastAPI)

**API Endpoints:**
- `src/backend/v3/api/dataset_router.py` - Handles `/v3/datasets/*` routes
  - `POST /upload` - Upload CSV/Excel files
  - `GET /` - List all datasets
  - `DELETE /{dataset_id}` - Delete dataset
  - `GET /{dataset_id}/download` - Download dataset

**Storage:**
- Files stored in `data/datasets/`
- Metadata tracked in memory or database
- MCP server reads from same directory

### MCP Server (Python/FastMCP)

**Server Setup:**
```python
# src/mcp_server/mcp_server.py
factory = MCPToolFactory()

# Register all services
factory.register_service(FinanceService())
factory.register_service(CustomerAnalyticsService())
factory.register_service(OperationsAnalyticsService())
factory.register_service(PricingAnalyticsService())
factory.register_service(MarketingAnalyticsService())
# ... other services

# Create FastMCP server
mcp = factory.create_mcp_server(name="MACAE MCP Server")
```

**Tool Registration:**
```python
# Each service registers its tools
class FinanceService(MCPToolBase):
    def register_tools(self, mcp: FastMCP):
        @mcp.tool()
        def list_finance_datasets() -> str:
            """List all available financial datasets."""
            # Implementation
        
        @mcp.tool()
        def generate_financial_forecast(...) -> str:
            """Generate forecast with advanced methods."""
            # Implementation
```

---

## 🔌 Semantic Kernel Integration

### MCP Plugin Creation

**Step 1: Agent Receives MCP Config**
```python
# src/backend/v3/magentic_agents/models/agent_models.py
@dataclass
class MCPConfig:
    url: str  # MCP server endpoint
    name: str  # Plugin name
    description: str
    tenant_id: str
    client_id: str
    
    @classmethod
    def from_env(cls) -> "MCPConfig":
        return cls(
            url=config.MCP_SERVER_ENDPOINT,  # http://localhost:8001
            name=config.MCP_SERVER_NAME,      # "MACAE MCP Server"
            description=config.MCP_SERVER_DESCRIPTION,
            tenant_id=config.AZURE_TENANT_ID,
            client_id=config.AZURE_CLIENT_ID,
        )
```

**Step 2: Agent Factory Reads Team Config**
```python
# src/backend/v3/magentic_agents/magentic_agent_factory.py
async def create_agent_from_config(self, agent_obj: SimpleNamespace):
    # Check if agent should use MCP
    use_mcp = getattr(agent_obj, 'use_mcp', False)
    
    # Create MCP config if enabled
    mcp_config = MCPConfig.from_env() if use_mcp else None
    
    # Create agent with MCP config
    if use_reasoning:
        agent = ReasoningAgentTemplate(
            agent_name=agent_obj.name,
            # ...
            mcp_config=mcp_config  # ← Passed to agent
        )
    else:
        agent = FoundryAgentTemplate(
            agent_name=agent_obj.name,
            # ...
            mcp_config=mcp_config  # ← Passed to agent
        )
    
    await agent.open()  # ← Initializes MCP plugin
    return agent
```

**Step 3: MCPEnabledBase Initializes Plugin**
```python
# src/backend/v3/magentic_agents/common/lifecycle.py
class MCPEnabledBase:
    async def _enter_mcp_if_configured(self) -> None:
        if not self.mcp_cfg:
            return
        
        # Create MCPStreamableHttpPlugin
        plugin = MCPStreamableHttpPlugin(
            name=self.mcp_cfg.name,
            description=self.mcp_cfg.description,
            url=self.mcp_cfg.url,  # ← Connects to MCP server
        )
        
        # Enter async context
        self.mcp_plugin = await self._stack.enter_async_context(plugin)
```

**Step 4: Agent Adds Plugin to Semantic Kernel**

*For Reasoning Agents (o1-preview):*
```python
# src/backend/v3/magentic_agents/reasoning_agent.py
async def _after_open(self) -> None:
    self.kernel = Kernel()
    
    # Add Azure OpenAI service
    chat = AzureChatCompletion(...)
    self.kernel.add_service(chat)
    
    # ✨ Add MCP plugin to kernel
    if self.mcp_plugin:
        self.kernel.add_plugin(
            self.mcp_plugin, 
            plugin_name="mcp_tools"  # ← All tools accessible as mcp_tools.*
        )
    
    # Create agent
    self._agent = ChatCompletionAgent(
        kernel=self.kernel,
        name=self.agent_name,
        # ...
    )
```

*For Foundry Agents (gpt-4):*
```python
# src/backend/v3/magentic_agents/foundry_agent.py
async def _after_open(self) -> None:
    # Create agent definition in Foundry
    definition = await self.client.agents.create_agent(
        model=self.model_deployment_name,
        name=self.agent_name,
        # ...
    )
    
    # ✨ Add MCP plugin
    plugins = [self.mcp_plugin] if self.mcp_plugin else []
    
    self._agent = AzureAIAgent(
        client=self.client,
        definition=definition,
        plugins=plugins  # ← Plugin added to agent
    )
```

---

## 🎯 How Agents Call MCP Tools

### Option 1: Automatic Tool Discovery (Semantic Kernel)

When an agent is initialized with an MCP plugin, Semantic Kernel automatically:
1. Queries the MCP server for available tools
2. Adds them to the kernel's function registry
3. Makes them available for the LLM to call

**Example Agent System Message:**
```python
system_message = """
You are a Financial Forecasting Specialist.

Available tools: 
- generate_financial_forecast
- evaluate_forecast_models
- list_finance_datasets
- summarize_financial_dataset

Use these tools to analyze data and create forecasts.
"""
```

### Option 2: Explicit Tool Calls (Agent Team Config)

**Agent Team JSON:**
```json
{
  "agents": [
    {
      "name": "FinanceForecastingAgent",
      "deployment_name": "gpt-4.1-mini",
      "use_mcp": true,  ← Enables MCP plugin
      "system_message": "You are a forecasting expert. Use MCP tools: generate_financial_forecast, evaluate_forecast_models, list_finance_datasets.",
      "description": "Forecasts revenue using advanced algorithms"
    }
  ]
}
```

**How it works:**
1. User asks: "Forecast revenue for next 6 months"
2. Agent sees `use_mcp: true` in config
3. MagenticAgentFactory creates `MCPConfig.from_env()`
4. Agent is initialized with MCP plugin
5. Semantic Kernel discovers all MCP tools
6. Agent can call `generate_financial_forecast(...)` naturally

---

## ✅ Current Status - What Works

### ✅ MCP Server
- All 9 services registered and working
- 25+ MCP tools available
- FastMCP server runs on port 8001
- Tools tested via Sprint 1-3 test suites

### ✅ Agent Team Configurations
- 8 agent teams configured
- All have `use_mcp: true` for specialized agents
- System messages list available tools
- Team configs match platform schema

### ✅ Frontend Drag & Drop
- Dataset upload works
- Multi-file upload supported
- Files stored in `data/datasets/`
- MCP tools can access uploaded files

### ✅ Backend API
- `/v3/datasets/*` endpoints functional
- Upload, list, delete, download all working
- Analytics endpoints created (`/v3/analytics/*`)

### ✅ Semantic Kernel Integration
- `MCPStreamableHttpPlugin` properly initialized
- Plugins added to Reasoning & Foundry agents
- Tool discovery automatic
- Agent can invoke MCP tools

---

## ⚠️ Potential Issues & Fixes

### Issue 1: MCP Server Not Running

**Symptom:** Agents can't call MCP tools, get connection errors

**Fix:**
```bash
# Start MCP server
cd src/mcp_server
python -m mcp_server

# Or via Docker
docker-compose up mcp-server
```

**Environment Variable:**
```bash
MCP_SERVER_ENDPOINT=http://localhost:8001
MCP_SERVER_NAME="MACAE MCP Server"
MCP_SERVER_DESCRIPTION="Multi-Agent Custom Automation Engine MCP Tools"
```

### Issue 2: Agent Not Configured for MCP

**Symptom:** Agent doesn't use MCP tools even though they're available

**Check:**
```json
// In agent team JSON
{
  "agents": [
    {
      "name": "YourAgent",
      "use_mcp": true,  ← Must be true
      "system_message": "... Available tools: tool1, tool2, ..."  ← List tools
    }
  ]
}
```

**Fix:** Ensure all specialized agents have:
1. `"use_mcp": true`
2. System message mentions available tools
3. Agent isn't ProxyAgent (ProxyAgent doesn't use MCP)

### Issue 3: Dataset Not Found

**Symptom:** MCP tool says dataset not found after upload

**Root Cause:** MCP server and backend use different directories

**Check:**
```python
# Backend uploads to:
data/datasets/

# MCP server reads from:
# Configured in mcp_server/config/settings.py
DATASET_PATH = Path("../../data/datasets/")
```

**Fix:** Ensure both use the same path (already configured correctly)

### Issue 4: Tool Names Don't Match

**Symptom:** Agent tries to call a tool but it doesn't exist

**Check Tool Registry:**
```python
# All registered MCP tools:
# Finance:
- list_finance_datasets
- summarize_financial_dataset
- generate_financial_forecast
- evaluate_forecast_models
- calculate_financial_metrics

# Customer Analytics:
- analyze_customer_churn
- segment_customers
- predict_customer_lifetime_value
- analyze_sentiment_trends

# Operations Analytics:
- forecast_delivery_performance
- optimize_inventory
- analyze_warehouse_incidents
- get_operations_summary

# Pricing Analytics:
- competitive_price_analysis
- optimize_discount_strategy
- forecast_revenue_by_category

# Marketing Analytics:
- analyze_campaign_effectiveness
- predict_engagement
- optimize_loyalty_program
```

**Fix:** Update agent system messages to use exact tool names

---

## 🔧 Configuration Checklist

### Environment Variables (.env)

```bash
# MCP Server
MCP_SERVER_ENDPOINT=http://localhost:8001
MCP_SERVER_NAME=MACAE MCP Server
MCP_SERVER_DESCRIPTION=Multi-Agent Custom Automation Engine MCP Tools

# Azure
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/

# Dataset Storage
DATASET_PATH=../../data/datasets/
```

### Agent Team JSON Schema

```json
{
  "id": "5",
  "team_id": "team-your-team",
  "name": "Your Team Name",
  "agents": [
    {
      "name": "YourAgent",
      "deployment_name": "gpt-4.1-mini",
      "use_mcp": true,  ← REQUIRED
      "use_rag": false,
      "use_bing": false,
      "use_reasoning": false,
      "coding_tools": false,
      "system_message": "You are an expert. Available tools: tool1, tool2",  ← RECOMMENDED
      "description": "Agent description"
    }
  ]
}
```

---

## 🧪 Testing MCP Integration

### Test 1: Verify MCP Server Running
```bash
curl http://localhost:8001/health
# Should return: {"status": "healthy"}
```

### Test 2: List Available Tools
```bash
# Via MCP protocol
curl http://localhost:8001/tools/list
```

### Test 3: Upload Dataset & Verify Access
```bash
# 1. Upload via frontend (drag & drop)
# 2. Check backend storage
ls data/datasets/
# 3. Call MCP tool
curl -X POST http://localhost:8001/tools/list_finance_datasets
```

### Test 4: Agent Uses MCP Tool
```python
# Create agent with MCP enabled
agent_config = {
    "name": "TestAgent",
    "deployment_name": "gpt-4.1-mini",
    "use_mcp": True,
    "system_message": "Use list_finance_datasets to show available data."
}

# Agent should successfully call the tool
response = await agent.invoke("What datasets are available?")
```

---

## 🎓 Adding New MCP Tools

### Step 1: Create Tool in Service

```python
# src/mcp_server/services/your_service.py
class YourService(MCPToolBase):
    def __init__(self):
        super().__init__(domain=Domain.YOUR_DOMAIN)
    
    def register_tools(self, mcp: FastMCP):
        @mcp.tool()
        def your_new_tool(param1: str, param2: int) -> str:
            """
            Tool description for LLM.
            
            Args:
                param1: Description of param1
                param2: Description of param2
            
            Returns:
                Description of return value
            """
            # Implementation
            return result
    
    @property
    def tool_count(self) -> int:
        return 1  # Update count
```

### Step 2: Register Service

```python
# src/mcp_server/mcp_server.py
from services.your_service import YourService

factory.register_service(YourService())
```

### Step 3: Update Agent System Message

```json
{
  "system_message": "... Available tools: your_new_tool, ..."
}
```

### Step 4: Test Tool

```python
# tests/your_service_tests.py
def test_your_new_tool():
    result = your_new_tool("test", 42)
    assert result is not None
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  ┌───────────────────────┐    ┌─────────────────────────┐  │
│  │ ForecastDatasetPanel  │    │  AnalyticsDashboard     │  │
│  │  - Drag & Drop        │    │  - KPI Cards            │  │
│  │  - Upload CSV/Excel   │    │  - Charts               │  │
│  └───────────┬───────────┘    └───────────┬─────────────┘  │
│              │                             │                 │
│              └─────────────┬───────────────┘                 │
│                            │                                 │
│                    DatasetService.tsx                        │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │ HTTP POST/GET
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Dataset Router (/v3/datasets/*)           │  │
│  │  - POST /upload  - GET /  - DELETE /{id}             │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼─────────────────────────────┐  │
│  │           OrchestrationManager                       │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │     MagenticAgentFactory                     │   │  │
│  │  │  - Reads agent team JSON                     │   │  │
│  │  │  - Creates MCPConfig if use_mcp: true       │   │  │
│  │  │  - Initializes agents with MCP plugin        │   │  │
│  │  └──────────────────┬───────────────────────────┘   │  │
│  └─────────────────────┼───────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────▼───────────────────────────────┐  │
│  │         MCPEnabledBase / AzureAgentBase             │  │
│  │  - Creates MCPStreamableHttpPlugin                   │  │
│  │  - Connects to MCP server                            │  │
│  │  - Adds plugin to Semantic Kernel                    │  │
│  └─────────────────────┬───────────────────────────────┘  │
└────────────────────────┼─────────────────────────────────┘
                         │ HTTP (MCP Protocol)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP SERVER (FastMCP)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              MCPToolFactory                          │  │
│  │  - FinanceService (5 tools)                         │  │
│  │  - CustomerAnalyticsService (4 tools)               │  │
│  │  - OperationsAnalyticsService (4 tools)             │  │
│  │  - PricingAnalyticsService (3 tools)                │  │
│  │  - MarketingAnalyticsService (3 tools)              │  │
│  │  - HRService, MarketingService, etc.                │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                     │
│                       ↓                                     │
│              data/datasets/*.csv                            │
│              (Shared with backend)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Summary

### What's Working ✅
1. **Frontend → Backend**: Dataset upload via drag & drop
2. **Backend → Storage**: Files saved to `data/datasets/`
3. **MCP Server → Storage**: Tools read from same directory
4. **Agent → MCP**: Semantic Kernel plugin integration
5. **Tool Discovery**: Automatic via MCPStreamableHttpPlugin
6. **Agent Teams**: All configured with correct schema

### What Needs Attention ⚠️
1. **Ensure MCP server is running** before starting backend
2. **Verify environment variables** are set for MCP config
3. **Test end-to-end flow** with actual user scenarios
4. **Monitor logs** for connection errors during agent initialization

### Next Steps 🚀
1. Deploy MCP server alongside backend
2. Run end-to-end integration tests
3. Create user documentation for dataset upload flow
4. Add monitoring/health checks for MCP connectivity

