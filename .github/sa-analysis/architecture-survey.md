# MACE Architecture Survey

**SA**: Multi-Agent Custom Automation Engine Solution Accelerator (MACE / MACAE)  
**Repository**: https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator  
**Surveyed path**: `/home/donlee/temp/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator`  
**Surveyed commit**: `92b0f85e`  
**Architecture pattern**: JSON-configured multi-agent orchestration with Azure AI Search RAG, FastMCP tools, Cosmos DB state, React UI, Container Apps, App Service, Bicep/AVM, and azd hooks.

## 1. Directory Structure

```text
.
├── azure.yaml                         # Primary azd metadata and postdeploy instructions
├── azure_custom.yaml                  # azd service map for backend, mcp, frontend
├── data/
│   ├── agent_teams/                   # Runtime team JSON configs
│   └── datasets/                      # Packaged demo data for retail, RFP, contract compliance
├── infra/
│   ├── main.bicep                     # Default Bicep deployment
│   ├── main_custom.bicep              # Custom/azd-service-tagged deployment variant
│   ├── main.parameters.json
│   ├── main.waf.parameters.json
│   ├── modules/
│   └── scripts/                       # Team upload, data upload, Search indexing
├── src/
│   ├── App/                           # React/Vite frontend plus FastAPI static proxy server
│   ├── backend/                       # FastAPI backend and Agent Framework orchestration
│   └── mcp_server/                    # FastMCP service host and tool services
└── tests/ and src/tests/              # Python and e2e test assets
```

## 2. Configuration Surfaces

| Surface | Location | Format | Purpose |
|---|---|---|---|
| Agent teams | `data/agent_teams/*.json` | JSON | Defines teams, agents, RAG/MCP/reasoning flags, prompts, and starting tasks. |
| Sample/demo data | `data/datasets/**` | CSV, JSON, PDF, DOCX | Uploaded to Blob Storage and indexed into Azure AI Search for RAG teams. |
| MCP services | `src/mcp_server/services/*.py` and `src/mcp_server/core/factory.py` | Python | Defines tool services registered against `Domain` enum values. |
| Backend validation model | `src/backend/v4/common/services/team_service.py`, `src/backend/common/models/messages_af.py` | Python/Pydantic | Validates uploaded team JSON and persists team state. |
| Frontend team contract | `src/App/src/models/Team.tsx`, `src/App/src/components/common/TeamSelector.tsx`, `src/App/src/components/content/HomeInput.tsx` | TypeScript/React | Validates uploaded team JSON, displays team cards, renders starting tasks, and submits selected team IDs. |
| Deployment | `azure.yaml`, `azure_custom.yaml`, `infra/**/*.bicep`, `src/**/Dockerfile` | YAML, Bicep, Docker | Provisions and hosts backend, frontend, MCP, storage, Search, Cosmos, identity, monitoring, and model resources. |
| Runtime settings | `src/backend/v4/config/settings.py`, `src/backend/pyproject.toml`, `src/backend/requirements.txt`, `src/App/frontend_server.py` | Python, TOML, env | Controls Azure endpoints, auth, app settings, frontend proxying, and dependency shape. |

### Agent Team JSON Shape

The backend accepts uploaded JSON with at least top-level `name`, `status`, non-empty `agents`, and non-empty `starting_tasks`. Agent entries require `input_key`, `type`, `name`, and `icon`; non-proxy agents should include `deployment_name`, `system_message`, `description`, and capability flags. Starting tasks require `id`, `name`, `prompt`, `created`, `creator`, and `logo`.

The frontend adds stricter practical constraints:

- `src/App/src/components/common/TeamSelector.tsx` rejects uploads with more than 6 agents.
- Default team IDs and names are reserved: `team-1`, `team-2`, `team-3`, `team-clm-1`, `team-compliance-1`; `Human Resources Team`, `Product Marketing Team`, `Retail Customer Success Team`, `RFP Team`, `Contract Compliance Review Team`.
- `src/App/src/components/content/HomeInput.tsx` renders `starting_tasks[].name`, `starting_tasks[].prompt`, and `starting_tasks[].logo`.
- The Contract Compliance display name triggers a legal disclaimer; generated teams should avoid accidental name collisions.

## 3. Data Layer

Packaged data lives under `data/datasets/`. Retail uses CSV/JSON files under `data/datasets/retail/customer` and `data/datasets/retail/order`, while RFP and contract compliance use document folders under `data/datasets/rfp/{summary,risk,compliance}` and `data/datasets/contract_compliance/{summary,risk,compliance}`.

`infra/scripts/selecting_team_config_and_data.sh` uploads packaged files to Blob Storage and calls `infra/scripts/index_datasets.py`, which creates or updates Azure AI Search indexes with `id`, `content`, and `title` fields. `infra/scripts/upload_team_config.py` currently enumerates only the five packaged team config files, so generated teams must be uploaded through the UI/API or the script must be intentionally extended.

## 4. Agent and AI Components

The active backend is under `src/backend/v4/`. It uses Microsoft Agent Framework/Magentic orchestration, with agents built dynamically from uploaded `TeamConfiguration` data rather than hardcoded domain-specific classes. Capabilities are controlled through team JSON flags:

- `use_rag` reads Azure AI Search indexes named in `index_name`.
- `use_mcp` connects to the FastMCP server.
- `use_reasoning` selects reasoning model deployments such as `o4-mini`.
- `ProxyAgent` enables human clarification patterns when present.

MCP tools are organized through `src/mcp_server/core/factory.py`, where the `Domain` enum and `MCPToolFactory` register services such as HR, marketing, product, tech support, general, and data.

## 5. Integration Points

| Integration | Evidence | Notes |
|---|---|---|
| Azure OpenAI / Azure AI Foundry | `infra/main.bicep`, `src/backend/v4/magentic_agents/foundry_agent.py` | Model deployments include GPT and reasoning models. |
| Azure AI Search | `infra/main.bicep`, `infra/scripts/index_datasets.py`, team JSON `index_name` | RAG agents depend on named Search indexes. |
| Azure Cosmos DB | `infra/main.bicep`, `src/backend/v4/common/services/team_service.py` | Stores team/session/plan state; reset is destructive for user state. |
| Azure Blob Storage | `infra/scripts/selecting_team_config_and_data.sh`, `infra/scripts/index_datasets.py` | Stages files before indexing. |
| FastMCP | `src/mcp_server/`, backend env `MCP_SERVER_ENDPOINT` | Backend talks to MCP container app endpoint. |
| React frontend | `src/App/src/api/apiService.tsx`, `src/App/src/store/TeamService.tsx` | Calls `/api/v4/*` endpoints and uploads JSON team configs. |
| Entra/EasyAuth | `src/backend/auth/`, `infra/main.bicep` | User identity is passed through headers and stored with team configs. |

## 6. Business Rules Location

Most use-case behavior lives in `data/agent_teams/*.json`: agent names, descriptions, system prompts, capability flags, RAG index references, and starting task prompts. Domain actions live in MCP service Python files. Deployment, indexing, and sample-data activation rules live in `infra/scripts/*.sh`, `.ps1`, and Python helpers.

## 7. Extension Points

| Extension | Primary touch points | Activation requirement |
|---|---|---|
| New use case | `data/agent_teams/<usecase>.json`; optional `data/datasets/<usecase>/`; optional `src/mcp_server/services/<domain>_service.py` | Upload team JSON through UI/API; index new datasets if RAG is used; register MCP service if tools are added. |
| New industry | `data/agent_teams/<industry>_<scenario>.json`; `data/datasets/<industry>/`; optional `data/industry_packs/<industry>/` as a planning bundle | Promote team config and datasets into runtime paths; upload/reindex safely through `deploy-adaptation`. |
| New RAG index | Team JSON `agents[].index_name`; `infra/scripts/index_datasets.py`; Blob container/index variables in deployment scripts | Create or update Search index and upload source files. |
| New MCP domain | `src/mcp_server/core/factory.py`; `src/mcp_server/services/<domain>_service.py`; MCP server registration | Requires code change, tests, container rebuild, and redeploy. |
| UI terminology | `src/App/src/components/**`, `src/App/src/models/Team.tsx`, styles/assets | Build frontend and run UI smoke checks only when UI paths changed. |

## 8. Deployment and UI/Frontend Surfaces

Deployment is mixed:

- `azure.yaml` is the primary metadata file and has postdeploy hooks that instruct users to run `infra/scripts/selecting_team_config_and_data.sh` or `Selecting-Team-Config-And-Data.ps1`.
- `azure_custom.yaml` defines azd services: `backend` and `mcp` as `containerapp`, and `frontend` as `appservice` with frontend prepackage hooks.
- `infra/main.bicep` provisions Container Apps for backend and MCP and an App Service frontend using container image parameters.
- `infra/main_custom.bicep` adds an AVM ACR module and azd service tags for backend, mcp, and frontend.
- Dockerfiles exist at `src/backend/Dockerfile`, `src/mcp_server/Dockerfile`, and `src/App/Dockerfile`.

UI surfaces:

- Labels/copy: `HomeInput.tsx` title and placeholder, `TeamSelector.tsx` dialog/upload/error text, `RAIErrorCard.tsx`, content panels, and prompt cards.
- Forms/review: `ChatInput`, `TeamSelector`, plan approval/cancellation dialogs, plan panels, and task list components.
- Routes/components: `App.tsx` routes `/` and `/plan/:planId`, `HomePage`, `PlanPage`, `PlanChat*`, `TeamSelected`, `TeamSelector`.
- Assets/branding: `ContosoLogo.tsx`, Fluent UI icon mapping in `homeInput.tsx`, CSS modules/styles.
- Contract support: `Team.tsx`, `inputTask.tsx`, `apiService.tsx`, `TeamService.tsx`, and backend `messages_af.py`.

Frontend build and smoke signals:

- Build: `cd src/App && npm ci && npm run build`
- Lint: `cd src/App && npm run lint`
- Tests: `cd src/App && npm run test -- --run`
- Smoke: load `/`, open team selector, upload/select generated team JSON, verify team card, agent badges, starting task cards, and plan creation payload with `team_id`.

## 9. Publish and Validation Surface

```yaml
publish:
  surface: mixed
  rationale: >-
    MACE combines Container Apps for backend/MCP, App Service frontend hosting,
    Dockerfiles, Bicep/AVM IaC, azd hooks, and sample data/Search activation scripts.
  evidence:
    dockerfiles:
      - src/backend/Dockerfile
      - src/mcp_server/Dockerfile
      - src/App/Dockerfile
    bicep:
      - infra/main.bicep
      - infra/main_custom.bicep
      - infra/main.parameters.json
      - infra/main.waf.parameters.json
    avm_module_count: 32
    container_apps:
      - infra/main.bicep:1204
      - infra/main.bicep:1412
      - infra/main_custom.bicep:1231
      - infra/main_custom.bicep:1454
    app_service:
      - infra/main.bicep:1533
      - infra/main_custom.bicep:1582
    acr_or_registry:
      - infra/main.bicep:141
      - infra/main.bicep:150
      - infra/main.bicep:159
      - infra/main_custom.bicep:1199
    azure_yaml:
      - azure.yaml
      - azure_custom.yaml
    cascade_rejected:
      - containerized-acr alone is insufficient because frontend App Service and azd hooks are also in scope.
      - app-service-code alone is insufficient because backend and MCP are Container Apps.
      - azd-native alone is insufficient because Bicep/AVM and image deployment evidence determine command safety.
  services:
    - name: backend
      host: containerapp
      project: src/backend
      dockerfile: src/backend/Dockerfile
      image_env_var: AZURE_ENV_CONTAINER_REGISTRY_ENDPOINT plus backendContainerImageTag
      runtime: ""
    - name: mcp
      host: containerapp
      project: src/mcp_server
      dockerfile: src/mcp_server/Dockerfile
      image_env_var: AZURE_ENV_CONTAINER_REGISTRY_ENDPOINT plus MCPContainerImageTag
      runtime: ""
    - name: frontend
      host: appservice
      project: src/App
      dockerfile: src/App/Dockerfile
      image_env_var: AZURE_ENV_CONTAINER_REGISTRY_ENDPOINT plus frontendContainerImageTag
      runtime: python
  azure_yaml_hooks:
    postdeploy:
      - azure.yaml: hooks.postdeploy.windows/posix prints selecting_team_config_and_data commands
      - azure_custom.yaml: hooks.postdeploy.windows/posix prints selecting_team_config_and_data commands
    predeploy: []
    postprovision: []

ui_surface:
  evidence:
    labels_copy:
      - src/App/src/components/content/HomeInput.tsx
      - src/App/src/components/common/TeamSelector.tsx
      - src/App/src/components/errors/RAIErrorCard.tsx
    forms_review_steps:
      - src/App/src/commonComponents/modules/ChatInput.tsx
      - src/App/src/components/common/PlanCancellationDialog.tsx
      - src/App/src/components/content/PlanPanelLeft.tsx
      - src/App/src/components/content/PlanPanelRight.tsx
      - src/App/src/components/content/TaskList.tsx
    routes_components:
      - src/App/src/App.tsx
      - src/App/src/pages/HomePage.tsx
      - src/App/src/pages/PlanPage.tsx
      - src/App/src/components/common/TeamSelected.tsx
      - src/App/src/components/common/TeamSelector.tsx
    assets_branding:
      - src/App/src/commonComponents/imports/ContosoLogo.tsx
      - src/App/src/commonComponents/imports/MsftColor.tsx
      - src/App/src/models/homeInput.tsx
      - src/App/src/styles/TeamSelector.module.css
    validation_messages:
      - src/App/src/components/common/TeamSelector.tsx
      - src/App/src/store/TeamService.tsx
    frontend_constants:
      - src/App/src/models/homeInput.tsx
      - src/App/src/components/common/TeamSelector.tsx
    client_side_parsers_types:
      - src/App/src/models/Team.tsx
      - src/App/src/models/inputTask.tsx
      - src/App/src/api/apiService.tsx
      - src/App/src/store/TeamService.tsx
    api_payload_expectations:
      - src/backend/common/models/messages_af.py
      - src/backend/v4/common/services/team_service.py
      - src/backend/v4/api/router.py
  build_commands:
    - cd src/App && npm ci && npm run build
  smoke_checks:
    - Load the home page and confirm the selected team name, prompt cards, and team selector render.
    - Upload a generated team JSON through the team selector and verify duplicate/team-size validation behavior.
    - Start a plan and verify the request includes the selected team_id.

validation_capability:
  lint_tools:
    - name: flake8
      config: .flake8
      command: python3 -m flake8 src/backend src/mcp_server
    - name: eslint
      config: src/App/package.json
      command: cd src/App && npm run lint
  test_frameworks:
    - name: pytest
      config: pytest.ini
      command: python3 -m pytest
    - name: vitest
      config: src/App/package.json
      command: cd src/App && npm run test -- --run
  iac_build_commands:
    - az bicep build --file infra/main.bicep --stdout > /dev/null
    - az bicep build --file infra/main_custom.bicep --stdout > /dev/null
  schema_files:
    - data/agent_teams/hr.json
    - data/agent_teams/marketing.json
    - data/agent_teams/retail.json
    - data/agent_teams/rfp_analysis_team.json
    - data/agent_teams/contract_compliance_team.json
    - src/backend/common/models/messages_af.py
    - src/App/src/models/Team.tsx
  cross_layer_pairs:
    - name: team-json-to-backend-model
      kind: 1to1-map
      producer: data/agent_teams/*.json
      consumer: src/backend/common/models/messages_af.py and src/backend/v4/common/services/team_service.py
    - name: team-json-to-frontend-teamconfig
      kind: 1to1-map
      producer: data/agent_teams/*.json
      consumer: src/App/src/models/Team.tsx and src/App/src/components/common/TeamSelector.tsx
    - name: rag-index-name-to-deployment-outputs
      kind: enum-membership
      producer: infra/main.bicep outputs and vars for AZURE_AI_SEARCH_INDEX_NAME_*
      consumer: data/agent_teams/*.json agents[].index_name
```
