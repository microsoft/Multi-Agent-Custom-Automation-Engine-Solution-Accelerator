# Duplicate `fc_` item ID in Magentic progress ledger when participants use tools

## Package versions

- `agent-framework==1.2.2`
- `agent-framework-foundry==1.2.2`
- Azure OpenAI Responses API (model: `gpt-4.1-mini`)
- Python 3.11, Windows 11

## Summary

When a Magentic workflow has **two or more tool-bearing participant agents**, the progress ledger call after the second participant completes fails with:

```text
Error code: 400 - {
  "error": {
    "message": "Duplicate item found with id fc_096e046ff5c43533006a03ac161b8c81978b5ccfbaebec0b3e. Remove duplicate items from your input and try again.",
    "type": "invalid_request_error",
    "param": "input",
    "code": null
  }
}
```

The framework catches this as `"Progress ledger creation failed, triggering reset"` and enters a reset → replan → reset loop that never converges.

## Root cause analysis

The bug is in `_MagenticManager._complete()` (`agent_framework_orchestrations/_magentic.py`, line 592):

```python
async def _complete(self, messages: list[Message]) -> Message:
    response: AgentResponse = await self._agent.run(messages, session=self._session)
    ...
```

This method sends **both**:

1. The full `messages` list (which is `[*chat_history, new_prompt]`) as explicit API **input**
2. `session=self._session`, which chains via **`previous_response_id`** — so the API also loads all items from the prior response chain server-side

After the first participant runs, `_handle_response` (line 964) appends the participant's response messages — which contain `function_call` and `function_call_output` items with `fc_` IDs — to `magentic_context.chat_history`.

The **first** progress ledger call succeeds because the `fc_` items are new to the session chain. But the session now stores this response ID. On the **second** progress ledger call (after another participant runs), the same `chat_history` still contains the first participant's `fc_` items. They appear:

- **Explicitly** in the `messages` parameter (via `chat_history`)
- **Implicitly** in the `previous_response_id` chain (from the prior progress ledger call)

The Responses API rejects the duplicate.

## Reproduction sequence

```text
1. MagenticBuilder(participants=[AgentA_with_tools, AgentB_with_tools],
                   manager_agent=manager, enable_plan_review=True).build()

2. workflow.run("task requiring both agents", stream=True)

3. Manager creates plan → _complete() calls succeed → session stores response IDs

4. Plan approved → inner loop starts

5. AgentA runs → calls tools → response.messages contain fc_ items
   → _handle_response → chat_history.extend(messages_with_fc_items)

6. Manager calls create_progress_ledger() →
   _complete([*chat_history_with_fc_items, prompt], session=self._session)
   → SUCCEEDS — fc_ items are new to session chain
   → Session stores this response as previous_response_id

7. AgentB runs → calls tools → response.messages added to chat_history

8. Manager calls create_progress_ledger() again →
   _complete([*chat_history_still_has_AgentA_fc_items, prompt], session=self._session)
   → chat_history contains AgentA's fc_ items (from step 5)
   → previous_response_id chain already has AgentA's fc_ items (from step 6)
   → API returns 400: "Duplicate item found with id fc_..."
```

## Observed behavior

```text
executor_completed  executor=TechnicalSupportAgent
superstep_completed
superstep_started
executor_invoked    executor=magentic_orchestrator
group_chat          GroupChatResponseReceivedEvent
Magentic Orchestrator: Progress ledger creation failed, triggering reset:
  "Duplicate item found with id fc_096e046ff5c43533006a03ac161b8c81978b5ccfbaebec0b3e"
request_info        MagenticPlanReviewRequest       ← reset triggered re-plan
executor_invoked    MagenticResetSignal  executor=HRHelperAgent
executor_invoked    MagenticResetSignal  executor=TechnicalSupportAgent
status              (workflow idles, never converges)
```

## Expected behavior

The progress ledger call after the second participant should succeed, and the orchestrator should evaluate task completion and either dispatch additional work or produce a final answer.

## Suggested fix

The `_complete` method should not send messages that are already in the `previous_response_id` chain. Two possible approaches:

### Option A: Track and send only new messages

```python
async def _complete(self, messages: list[Message]) -> Message:
    # Only send messages added since the last _complete call
    new_messages = messages[self._last_sent_count:]
    response = await self._agent.run(new_messages, session=self._session)
    self._last_sent_count = len(messages)
    ...
```

### Option B: Don't use session chaining for the manager

```python
async def _complete(self, messages: list[Message]) -> Message:
    # Send full chat_history without session chaining
    response = await self._agent.run(messages)
    ...
```

Option A preserves the session chain benefits (token efficiency). Option B is simpler but re-sends full context each time.

### Option C: Strip function_call items from participant messages before adding to chat_history

This would lose tool-call context from the progress ledger's perspective, so it may reduce orchestration quality.

## Minimal reproduction

See [`repro_duplicate_fc_id.py`](repro_duplicate_fc_id.py) in the same directory — a single-file script that creates a two-agent Magentic workflow with simple tool-bearing participants and triggers the error.

## Workaround

Currently there is no clean workaround at the application level. The `chat_history` and session are managed internally by `_MagenticManager`. The only partial mitigation is to use a single participant agent (avoiding the second progress ledger call), but this defeats the purpose of multi-agent orchestration.
