# ADR-003: Reasoning Model (o4-mini) for Orchestrator Manager

## Status

Accepted

## Date

2026-05-19

> **Note (2026-06):** The participant-agent baseline referenced throughout this
> ADR (`gpt-4.1` / `gpt-4.1-mini`) has since been migrated to the GPT-5.4
> family (`gpt-5.4` / `gpt-5.4-mini`). The decision below — that the orchestrator
> manager uses a dedicated reasoning model (`o4-mini`) independent of the team
> model — still applies. GPT-5.4 is itself a reasoning model, so the gap
> between manager and participants is now smaller, but `o4-mini` is retained
> for the manager because it is specifically tuned for low-latency routing
> decisions and structured JSON output.

## Context

The Magentic orchestrator uses a `StandardMagenticManager` agent to make routing decisions: creating a plan, selecting the next speaker via a JSON progress ledger, and determining workflow completion. These decisions require:

1. **Reliable structured JSON output** — the progress ledger must parse as valid JSON with specific fields (`next_speaker`, `is_request_satisfied`, etc.).
2. **Multi-step conditional logic** — routing rules like "if a domain agent needs user info, select UserInteractionAgent next" are embedded in long prompts with multiple competing instructions.
3. **Instruction compliance** — the manager must follow plan rules, completion checks, and clarification policies without skipping or hallucinating.

Previously, the manager shared a single `FoundryChatClient` with all participant agents, using the team's `deployment_name` (typically `gpt-4.1`). This caused **non-deterministic routing failures** (Bug B1): the manager would intermittently fail to select `UserInteractionAgent` when domain agents signaled they needed user clarification, either hanging or proceeding with fabricated data.

### Root Cause

Standard GPT models (gpt-4o, gpt-4.1) are optimized for general-purpose chat. They are less reliable at:

- Following deeply nested conditional routing logic in long system prompts
- Producing structurally valid JSON under all conditions
- Resisting the tendency to "complete" a task rather than routing to another agent

Reasoning models (o-series) are explicitly designed for multi-step logical reasoning and structured output, making them significantly more reliable for orchestration decisions.

### Model Options Evaluated

| Model | Reasoning | Structured JSON | Latency | Cost | Verdict |
|-------|-----------|-----------------|---------|------|---------|
| o4-mini | Yes | Excellent | Low (for reasoning) | Low | **Selected** |
| o3 | Yes | Excellent | High | High | Overkill for routing |
| gpt-4.1 | No | Good | Low | Low | Current — unreliable for routing |
| gpt-4.1-mini | No | Adequate | Very low | Very low | Too weak for complex routing |
| gpt-4.1-nano | No | Basic | Ultra-low | Ultra-low | Insufficient for orchestration |

## Decision

We will **use a separate reasoning model (`o4-mini` by default) for the MagenticManager** agent, independent of the model used by participant agents.

- A new config `ORCHESTRATOR_MODEL_NAME` (default: `o4-mini`) controls the manager's model.
- A separate `FoundryChatClient` is created for the manager at workflow initialization.
- Participant agents continue using the team's `deployment_name` (e.g., `gpt-4.1`).
- If the orchestrator model deployment fails to initialize, it falls back to the team model with a warning.

## Implementation

### Config change

`common/config/app_config.py`:

```python
self.ORCHESTRATOR_MODEL_NAME = self._get_optional("ORCHESTRATOR_MODEL_NAME", "o4-mini")
```

### Orchestration change

`orchestration/orchestration_manager.py` — `init_orchestration()`:

```python
# Participant agents use team model
chat_client = FoundryChatClient(
    project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
    model=team_config.deployment_name,
    credential=credential,
)

# Manager uses reasoning model for reliable routing
manager_chat_client = FoundryChatClient(
    project_endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
    model=config.ORCHESTRATOR_MODEL_NAME,
    credential=credential,
)

manager_agent = Agent(manager_chat_client, name="MagenticManager")
```

## Alternatives Considered

### Keep Single Model, Strengthen Prompts

- **Pros:** No additional model deployment; simpler architecture.
- **Cons:** Already attempted — extensive prompt engineering (USER CLARIFICATION POLICY, EXECUTION RULES, COMPLETION CHECK) did not eliminate the non-deterministic failures. The issue is fundamental to how non-reasoning models handle complex conditional logic.

### Use o3 for Manager

- **Pros:** Maximum reasoning capability.
- **Cons:** Significantly more expensive and slower. The orchestrator runs multiple inference calls per workflow (plan + one ledger per round). `o4-mini` provides equivalent routing reliability at a fraction of the cost/latency.

### Use Structured Outputs (JSON Mode) with gpt-4.1

- **Pros:** Guarantees valid JSON structure.
- **Cons:** JSON mode only ensures syntactic validity, not semantic correctness. The model still skips routing logic (selects wrong agent or marks complete prematurely). The issue is reasoning quality, not output format.

## Consequences

- **Positive:** Eliminates non-deterministic routing failures for UserInteractionAgent. Manager reliably follows plan structure and completion checks. Unblocks all interactive scenarios (HR onboarding).
- **Positive:** Minimal cost impact — manager makes 3–8 calls per workflow; `o4-mini` is inexpensive per call.
- **Negative:** Requires `o4-mini` model deployment in the Foundry project. Adds one additional `FoundryChatClient` instance per workflow.
- **Mitigation:** Fallback to team model if orchestrator model unavailable. `ORCHESTRATOR_MODEL_NAME` is configurable — teams can switch models without code changes.

## References

- [Bug B1: UserInteractionAgent Routing Failure](../../localspec/bugs/user-interaction-routing.md)
- [ADR-001: Retain Custom JSON Configuration](./001-retain-custom-json-declarative-config.md)
- [Azure AI Foundry Model Catalog](https://ai.azure.com/explore/models)
