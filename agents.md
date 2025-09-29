# Agents Reference

## Repository Snapshot
- **Domain focus:** Multi-agent automation solution with backend services, web frontend, and MCP integration.
- **Environments & tooling:** Azure DevOps pipeline configs in `.azdo/`, GitHub workflow definitions in `.github/`, and dev container setup under `.devcontainer/`.
- **Deployment:** Primary Bicep templates and parameter sets live in `infra/`.

## Top-Level Directories
| Path | Purpose |
| --- | --- |
| `.azdo/pipelines/azure-dev.yml` | Azure DevOps build/deploy pipeline definition. |
| `.devcontainer/` | VS Code dev container configuration for consistent local environments. |
| `.github/` | GitHub metadata including workflows, issue templates, CODEOWNERS, and PR template. |
| `data/agent_teams/` | JSON definitions of predefined agent teams (HR, marketing, retail). |
| `data/datasets/` | Synthetic CSV/JSON datasets agents can consume during scenarios. |
| `docs/` | Operational runbooks: Azure setup, deployment guides, troubleshooting, and MCP testing. |
| `infra/` | Bicep infrastructure modules, parameters, and helper scripts for Azure provisioning. |
| `src/` | Application source code (backend services, frontend app, MCP server, shared tests). |
| `tests/e2e-test/` | End-to-end automation suites targeting deployed environments. |

## Application Source Layout (`src/`)
- `backend/`: Python FastAPI services with modules for auth, middleware, shared utilities, and versioned APIs (`v3/`). Contains Dockerfiles, `pyproject.toml`, and `app_kernel.py` entry point.
- `frontend/`: Vite/React TypeScript client with accompanying Python `frontend_server.py` for serving, plus Dockerfile and Vitest config.
- `mcp_server/`: Modular MCP server with `config/`, `core/`, `services/`, and `utils/`; ships Docker assets, pytest config, and environment samples.
- `tests/`: Service-level Python tests colocated with each component.

## Infrastructure (`infra/`)
- `main.bicep` / `main_custom.bicep`: Full environment provisioning templates with parameter defaults in `main.parameters.json` and `main.waf.parameters.json`.
- `modules/`: Reusable Bicep modules (review for resource-specific deployments before customization).
- `scripts/`: Automation helpers for deployment and maintenance workflows.

## Operational Notes
- Environment samples (`.env.sample`, `.env.example`) reside in each service directory; copy and adjust per environment.
- `azure.yaml` and `azure_custom.yaml` define azd environment mappings; align MCP and web app settings with these.
- Root Python tooling: `.flake8`, `pytest.ini`, and `conftest.py` configure linting and shared fixtures.
- Security and support policies are in `SECURITY.md`, `SUPPORT.md`, and `TRANSPARENCY_FAQS.md` for quick reference.

## Testing & Quality
- Python: run `pytest` from the repo root or service directories; backend and MCP server include dedicated `pyproject.toml` definitions.
- Frontend: use `npm test` (Vitest) within `src/frontend/`.
- E2E: execute suites in `tests/e2e-test/` once infrastructure is provisioned.
