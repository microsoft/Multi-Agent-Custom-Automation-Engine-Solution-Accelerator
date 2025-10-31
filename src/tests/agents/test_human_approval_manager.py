import sys
from pathlib import Path

import pytest

# Add the backend path to sys.path so we can import v3 modules
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from v3.models.models import MPlan, MStep
from v3.orchestration.human_approval_manager import \
    HumanApprovalMagenticManager

#
# Helper dummies to simulate the minimal shape required by plan_to_obj
#

class _Obj:
    def __init__(self, content: str):
        self.content = content

class DummyLedger:
    def __init__(self, plan_content: str, facts_content: str = ""):
        self.plan = _Obj(plan_content)
        self.facts = _Obj(facts_content)

class DummyContext:
    def __init__(self, task: str, participant_descriptions: dict[str, str]):
        self.task = task
        self.participant_descriptions = participant_descriptions


def _make_manager():
    """
    Create a HumanApprovalMagenticManager instance without calling its __init__
    (avoids needing the full semantic kernel dependencies for this focused unit test).
    """
    return HumanApprovalMagenticManager.__new__(HumanApprovalMagenticManager)

def test_plan_to_obj_basic_parsing():
    plan_text = """
- **ProductAgent** to provide detailed information about the company's current products.  
- **MarketingAgent** to gather relevant market positioning insights, key messaging strategies.  
- **MarketingAgent** to draft an initial press release outline based on the product details.  
- **ProductAgent** to review the press release outline for technical accuracy and completeness of product details.  
- **MarketingAgent** to finalize the press release draft incorporating the ProductAgent’s feedback.  
- **ProxyAgent** to step in and request additional clarification or missing details from ProductAgent and MarketingAgent.
"""
    ctx = DummyContext(
        task="Analyze Q4 performance",
        participant_descriptions={
            "ProductAgent": "Provide product info",
            "MarketingAgent": "Handle marketing",
            "ProxyAgent": "Ask user for missing info",
        },
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)

    assert isinstance(mplan, MPlan)
    assert mplan.user_request == "Analyze Q4 performance"
    assert len(mplan.steps) == 6

    agents = [s.agent for s in mplan.steps]
    assert agents == ["ProductAgent", "MarketingAgent", "MarketingAgent","ProductAgent", "MarketingAgent", "ProxyAgent"]

    actions = [s.action for s in mplan.steps]
    assert "to provide detailed information about the company's current products" in actions[0]
    assert "to gather relevant market positioning insights, key messaging strategies" in actions[1].lower()
    assert "to draft an initial press release outline based on the product details" in actions[2]
    assert "to review the press release outline for technical accuracy and completeness of product details" in actions[3]
    assert "to finalize the press release draft incorporating the productagent’s feedback" in actions[4].lower()
    assert "to step in and request additional clarification or missing details from productagent and marketingagent" in actions[5].lower()


def test_plan_to_obj_ignores_non_bullet_lines_and_uses_fallback():
    plan_text = """
Introduction line that should be ignored
- **ResearchAgent** to collect competitor pricing
Some trailing commentary
- finalize compiled dataset
"""
    ctx = DummyContext(
        task="Compile competitive pricing dataset",
        participant_descriptions={
            "ResearchAgent": "Collect data",
        },
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)

    # Only 2 bullet lines
    assert len(mplan.steps) == 2
    assert mplan.steps[0].agent == "ResearchAgent"
    # Second bullet has no recognizable agent => fallback
    assert mplan.steps[1].agent == "MagenticAgent"
    assert "finalize compiled dataset" in mplan.steps[1].action.lower()


def test_plan_to_obj_resets_agent_each_line():
    plan_text = """
- **ResearchAgent** to gather initial statistics
- finalize normalizing collected values
"""
    ctx = DummyContext(
        task="Normalize stats",
        participant_descriptions={
            "ResearchAgent": "Collect data",
        },
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)

    assert len(mplan.steps) == 2
    assert mplan.steps[0].agent == "ResearchAgent"
    # Ensure no leakage of previous agent
    assert mplan.steps[1].agent == "MagenticAgent"


@pytest.mark.xfail(reason="Current implementation duplicates text when a line ends with ':' due to prefix handling.")
def test_plan_to_obj_colon_prefix_current_behavior():
    plan_text = """
- **ResearchAgent** to gather quarterly metrics:
"""
    ctx = DummyContext(
        task="Quarterly metrics",
        participant_descriptions={
            "ResearchAgent": "Collect metrics",
        },
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)

    # Expect 1 step
    assert len(mplan.steps) == 1
    # Current code creates duplicated phrase if colon is present (likely a bug)
    action = mplan.steps[0].action
    # This assertion documents present behavior; adjust when you fix prefix logic.
    assert action.count("gather quarterly metrics") == 1  # Will fail until fixed


def test_plan_to_obj_empty_or_whitespace_plan():
    plan_text = "   \n \n"
    ctx = DummyContext(
        task="Empty plan test",
        participant_descriptions={
            "AgentA": "A",
        },
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)
    assert len(mplan.steps) == 0
    assert mplan.user_request == "Empty plan test"


def test_plan_to_obj_multiple_agents_case_insensitive():
    plan_text = """
- **researchagent** to collect raw feeds
- **ANALYSISAGENT** to process raw feeds
"""
    ctx = DummyContext(
        task="Case insensitivity test",
        participant_descriptions={
            "ResearchAgent": "Collect",
            "AnalysisAgent": "Process",
        },
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)
    assert [s.agent for s in mplan.steps] == ["ResearchAgent", "AnalysisAgent"]


def test_plan_to_obj_facts_copied():
    plan_text = "- **ResearchAgent** to gather X"
    facts_text = "Known constraints: Budget capped."
    ctx = DummyContext(
        task="Gather X",
        participant_descriptions={"ResearchAgent": "Collect"},
    )
    ledger = DummyLedger(plan_text, facts_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)
    assert mplan.facts == "Known constraints: Budget capped."
    assert len(mplan.steps) == 1
    assert mplan.steps[0].agent == "ResearchAgent"


def test_plan_to_obj_fallback_when_agent_not_in_team():
    plan_text = "- **UnknownAgent** to do something unusual"
    ctx = DummyContext(
        task="Unknown agent test",
        participant_descriptions={"ResearchAgent": "Collect"},
    )
    ledger = DummyLedger(plan_text)
    mgr = _make_manager()

    mplan = mgr.plan_to_obj(ctx, ledger)
    assert len(mplan.steps) == 1
    assert mplan.steps[0].agent == "MagenticAgent"
    assert "do something unusual" in mplan.steps[0].action.lower()