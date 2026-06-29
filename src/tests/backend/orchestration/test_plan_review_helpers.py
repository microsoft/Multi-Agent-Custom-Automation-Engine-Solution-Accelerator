"""Unit tests for plan_review_helpers module.

Tests the three public functions:
- get_magentic_prompt_kwargs()
- convert_plan_review_to_mplan()
- wait_for_plan_approval()
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock

import pytest

# Set up required environment variables before any imports
os.environ.update({
    'APPLICATIONINSIGHTS_CONNECTION_STRING': 'InstrumentationKey=test-key',
    'APP_ENV': 'dev',
    'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
    'AZURE_OPENAI_API_KEY': 'test_key',
    'AZURE_OPENAI_DEPLOYMENT_NAME': 'test_deployment',
    'AZURE_AI_SUBSCRIPTION_ID': 'test_subscription_id',
    'AZURE_AI_RESOURCE_GROUP': 'test_resource_group',
    'AZURE_AI_PROJECT_NAME': 'test_project_name',
    'AZURE_AI_AGENT_ENDPOINT': 'https://test.agent.azure.com/',
    'AZURE_AI_PROJECT_ENDPOINT': 'https://test.project.azure.com/',
    'COSMOSDB_ENDPOINT': 'https://test.documents.azure.com:443/',
    'COSMOSDB_DATABASE': 'test_database',
    'COSMOSDB_CONTAINER': 'test_container',
    'AZURE_CLIENT_ID': 'test_client_id',
    'AZURE_TENANT_ID': 'test_tenant_id',
    'AZURE_OPENAI_RAI_DEPLOYMENT_NAME': 'test_rai_deployment',
})

# Mock external Azure dependencies
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.agents'] = Mock()
sys.modules['azure.ai.agents.aio'] = Mock(AgentsClient=Mock)
sys.modules['azure.ai.projects'] = Mock()
sys.modules['azure.ai.projects.aio'] = Mock(AIProjectClient=Mock)
sys.modules['azure.ai.projects.models'] = Mock(MCPTool=Mock)
sys.modules['azure.core'] = Mock()
sys.modules['azure.core.exceptions'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['azure.cosmos'] = Mock(CosmosClient=Mock)

# ---- Mock agent_framework prompt constants ----
ORCHESTRATOR_FINAL_ANSWER_PROMPT = "Final answer prompt"
ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT = "Task ledger plan prompt"
ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT = "Task ledger plan update prompt"
ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT = "Task ledger facts prompt"
ORCHESTRATOR_PROGRESS_LEDGER_PROMPT = "Progress ledger prompt"

sys.modules['agent_framework'] = Mock()
sys.modules['agent_framework_orchestrations'] = Mock()
sys.modules['agent_framework_orchestrations._magentic'] = Mock(
    ORCHESTRATOR_FINAL_ANSWER_PROMPT=ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT=ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT=ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT=ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT,
    ORCHESTRATOR_PROGRESS_LEDGER_PROMPT=ORCHESTRATOR_PROGRESS_LEDGER_PROMPT,
)

# ---- Mock models.messages ----
class MockWebsocketMessageType:
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    FINAL_RESULT_MESSAGE = "final_result_message"
    TIMEOUT_NOTIFICATION = "timeout_notification"


class MockPlanApprovalResponse:
    def __init__(self, approved=True, m_plan_id=None):
        self.approved = approved
        self.m_plan_id = m_plan_id


class MockTimeoutNotification:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


mock_messages_module = Mock()
mock_messages_module.WebsocketMessageType = MockWebsocketMessageType
mock_messages_module.PlanApprovalResponse = MockPlanApprovalResponse
mock_messages_module.TimeoutNotification = MockTimeoutNotification
mock_messages_module.PlanApprovalRequest = Mock

mock_models = Mock()
mock_models.messages = mock_messages_module
sys.modules['models'] = mock_models
sys.modules['models.messages'] = mock_messages_module

# ---- Mock orchestration.connection_config ----
mock_connection_config = Mock()
mock_connection_config.send_status_update_async = AsyncMock()

mock_orchestration_config = Mock()
mock_orchestration_config.max_rounds = 10
mock_orchestration_config.default_timeout = 30
mock_orchestration_config.plans = {}
mock_orchestration_config.approvals = {}
mock_orchestration_config.set_approval_pending = Mock()
mock_orchestration_config.wait_for_approval = AsyncMock(return_value=True)
mock_orchestration_config.cleanup_approval = Mock()

sys.modules['orchestration.connection_config'] = Mock(
    connection_config=mock_connection_config,
    orchestration_config=mock_orchestration_config,
)

# ---- Mock models.plan_models ----
class MockMStep:
    def __init__(self, agent="", action=""):
        self.agent = agent
        self.action = action


class MockMPlan:
    def __init__(self):
        self.id = "test-plan-id"
        self.user_id = None
        self.steps = []

sys.modules['models.plan_models'] = Mock(MPlan=MockMPlan, MStep=MockMStep)

# ---- Mock plan converter ----
class MockPlanToMPlanConverter:
    @staticmethod
    def convert(plan_text, facts, team, task):
        return MockMPlan()

sys.modules['orchestration.helper.plan_to_mplan_converter'] = Mock(
    PlanToMPlanConverter=MockPlanToMPlanConverter,
)

# ---- Import module under test ----
from backend.orchestration.plan_review_helpers import (
    convert_plan_review_to_mplan, get_magentic_prompt_kwargs,
    wait_for_plan_approval)

# Re-bind mocked singletons for convenient assertions
connection_config = sys.modules['orchestration.connection_config'].connection_config
orchestration_config = sys.modules['orchestration.connection_config'].orchestration_config


# =========================================================================
# get_magentic_prompt_kwargs
# =========================================================================
class TestGetMagenticPromptKwargs:
    """Test get_magentic_prompt_kwargs() prompt customization builder."""

    def test_given_no_user_responses_when_called_then_returns_base_keys(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=False)

        # Assert
        assert "task_ledger_plan_prompt" in result
        assert "task_ledger_plan_update_prompt" in result
        assert "final_answer_prompt" in result
        assert "task_ledger_facts_prompt" not in result
        # progress_ledger_prompt (completion enforcement) is now always present,
        # so plan-step agents must run even for teams without user_responses.
        assert "progress_ledger_prompt" in result

    def test_given_user_responses_when_called_then_returns_extended_keys(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=True)

        # Assert
        assert "task_ledger_plan_prompt" in result
        assert "task_ledger_plan_update_prompt" in result
        assert "final_answer_prompt" in result
        assert "task_ledger_facts_prompt" in result
        assert "progress_ledger_prompt" in result

    def test_given_no_user_responses_when_called_then_plan_has_zero_questions_policy(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=False)

        # Assert
        assert "ZERO QUESTIONS" in result["task_ledger_plan_prompt"]

    def test_given_user_responses_when_called_then_plan_has_work_first_policy(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=True)

        # Assert
        assert "USER CLARIFICATION POLICY" in result["task_ledger_plan_prompt"]

    def test_given_user_responses_when_called_then_progress_contains_execution_rules(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=True)

        # Assert
        assert "EXECUTION RULES" in result["progress_ledger_prompt"]
        assert "COMPLETION CHECK" in result["progress_ledger_prompt"]

    def test_given_no_user_responses_when_called_then_progress_still_enforces_completion(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=False)

        # Assert — completion enforcement applies even without user_responses
        assert "progress_ledger_prompt" in result
        assert "COMPLETION CHECK" in result["progress_ledger_prompt"]
        # User-clarification-only rules must NOT leak in for non-interactive teams
        assert "request_user_clarification" not in result["progress_ledger_prompt"]

    def test_given_participant_names_when_called_then_plan_lists_mandatory_agents(self):
        # Act
        result = get_magentic_prompt_kwargs(
            has_user_responses=False,
            participant_names=["TriageAgent", "ComplianceAgent"],
        )

        # Assert — every listed agent is required to appear in the plan
        plan_prompt = result["task_ledger_plan_prompt"]
        assert "MANDATORY AGENTS" in plan_prompt
        assert "- TriageAgent" in plan_prompt
        assert "- ComplianceAgent" in plan_prompt

    def test_given_no_participant_names_when_called_then_no_mandatory_block(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=False)

        # Assert
        assert "MANDATORY AGENTS" not in result["task_ledger_plan_prompt"]

    def test_given_no_user_responses_when_called_then_final_has_answer_rules(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=False)

        # Assert
        assert "FINAL ANSWER RULES" in result["final_answer_prompt"]

    def test_given_default_when_called_then_user_responses_is_false(self):
        # Act
        result = get_magentic_prompt_kwargs()

        # Assert
        assert "ZERO QUESTIONS" in result["task_ledger_plan_prompt"]

    def test_given_no_user_responses_when_called_then_plan_prompt_appends_base_prompt(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=False)

        # Assert — starts with the base prompt constant
        assert result["task_ledger_plan_prompt"].startswith(ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT)
        assert result["task_ledger_plan_update_prompt"].startswith(ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT)
        assert result["final_answer_prompt"].startswith(ORCHESTRATOR_FINAL_ANSWER_PROMPT)

    def test_given_user_responses_when_called_then_facts_prompt_appends_base_prompt(self):
        # Act
        result = get_magentic_prompt_kwargs(has_user_responses=True)

        # Assert
        assert result["task_ledger_facts_prompt"].startswith(ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT)
        assert result["progress_ledger_prompt"].startswith(ORCHESTRATOR_PROGRESS_LEDGER_PROMPT)


# =========================================================================
# convert_plan_review_to_mplan
# =========================================================================
class TestConvertPlanReviewToMplan:
    """Test convert_plan_review_to_mplan() ledger to MPlan conversion."""

    @staticmethod
    def _make_review_request(plan_text="Step plan", facts_text="Some facts"):
        """Build a mock MagenticPlanReviewRequest with nested ledger."""
        inner_plan = Mock()
        inner_plan.text = plan_text

        inner_facts = Mock()
        inner_facts.text = facts_text

        ledger = Mock()
        ledger.plan = inner_plan
        ledger.facts = inner_facts

        request = Mock()
        request.plan = ledger
        return request

    def test_given_valid_ledger_when_called_then_returns_mplan(self):
        # Arrange
        request = self._make_review_request()

        # Act
        result = convert_plan_review_to_mplan(
            request,
            participant_names=["Agent1", "Agent2"],
            task_text="Do something",
            user_id="user-1",
        )

        # Assert
        assert isinstance(result, MockMPlan)
        assert result.user_id == "user-1"

    def test_given_none_ledger_when_called_then_raises_value_error(self):
        # Arrange
        request = Mock()
        request.plan = None

        # Act & Assert
        with pytest.raises(ValueError, match="no plan data"):
            convert_plan_review_to_mplan(
                request,
                participant_names=[],
                task_text="task",
                user_id="user-1",
            )

    def test_given_ledger_missing_plan_attr_when_called_then_falls_to_plain_message_path(self):
        # Arrange — ledger with no .plan attr falls through to plain Message path
        ledger = Mock(spec=[])  # empty spec — no attributes
        ledger.text = "- **Agent1** to do something"
        request = Mock()
        request.plan = ledger

        # Act
        result = convert_plan_review_to_mplan(
            request,
            participant_names=["Agent1"],
            task_text="task",
            user_id="user-1",
        )

        # Assert — gracefully handled via plain-message path
        assert isinstance(result, MockMPlan)

    def test_given_ledger_missing_facts_attr_when_called_then_uses_empty_facts(self):
        # Arrange — ledger with .plan but no .facts uses empty string for facts
        ledger = Mock()
        ledger.plan = Mock()
        ledger.plan.text = "Step plan text"
        del ledger.facts
        request = Mock()
        request.plan = ledger

        # Act
        result = convert_plan_review_to_mplan(
            request,
            participant_names=["Agent1"],
            task_text="task",
            user_id="user-1",
        )

        # Assert — gracefully handled with empty facts
        assert isinstance(result, MockMPlan)


# =========================================================================
# wait_for_plan_approval
# =========================================================================
class TestWaitForPlanApproval:
    """Test wait_for_plan_approval() WebSocket-based approval gate."""

    def setup_method(self):
        """Reset mocks before each test."""
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None
        orchestration_config.set_approval_pending.reset_mock()
        orchestration_config.wait_for_approval.reset_mock()
        orchestration_config.wait_for_approval.return_value = True
        orchestration_config.cleanup_approval.reset_mock()

    @pytest.mark.asyncio
    async def test_given_approved_when_waiting_then_returns_approved_response(self):
        # Arrange
        orchestration_config.wait_for_approval.return_value = True

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is not None
        assert result.approved is True
        assert result.m_plan_id == "plan-1"
        orchestration_config.set_approval_pending.assert_called_with("plan-1")
        orchestration_config.wait_for_approval.assert_awaited_with("plan-1")

    @pytest.mark.asyncio
    async def test_given_rejected_when_waiting_then_returns_rejected_response(self):
        # Arrange
        orchestration_config.wait_for_approval.return_value = False

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is not None
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_given_no_plan_id_when_waiting_then_returns_rejected_response(self):
        # Act
        result = await wait_for_plan_approval(None, "user-1")

        # Assert
        assert result is not None
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_given_empty_plan_id_when_waiting_then_returns_rejected_response(self):
        # Act
        result = await wait_for_plan_approval("", "user-1")

        # Assert
        assert result is not None
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_given_timeout_when_waiting_then_returns_none(self):
        # Arrange
        orchestration_config.wait_for_approval.side_effect = asyncio.TimeoutError()

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is None
        connection_config.send_status_update_async.assert_awaited_once()
        orchestration_config.cleanup_approval.assert_called_with("plan-1")

    @pytest.mark.asyncio
    async def test_given_timeout_and_ws_error_when_waiting_then_returns_none(self):
        # Arrange
        orchestration_config.wait_for_approval.side_effect = asyncio.TimeoutError()
        connection_config.send_status_update_async.side_effect = Exception("WS down")

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is None
        orchestration_config.cleanup_approval.assert_called_with("plan-1")

    @pytest.mark.asyncio
    async def test_given_key_error_when_waiting_then_returns_none(self):
        # Arrange
        orchestration_config.wait_for_approval.side_effect = KeyError("missing")

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_given_cancelled_when_waiting_then_returns_none(self):
        # Arrange
        orchestration_config.wait_for_approval.side_effect = asyncio.CancelledError()

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is None
        orchestration_config.cleanup_approval.assert_called_with("plan-1")

    @pytest.mark.asyncio
    async def test_given_unexpected_error_when_waiting_then_returns_none(self):
        # Arrange
        orchestration_config.wait_for_approval.side_effect = RuntimeError("boom")

        # Act
        result = await wait_for_plan_approval("plan-1", "user-1")

        # Assert
        assert result is None
        orchestration_config.cleanup_approval.assert_called_with("plan-1")
