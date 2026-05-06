"""
Unit tests for plan_to_mplan_converter.py module.

This module tests the PlanToMPlanConverter class and its functionality for converting
bullet-style plan text into MPlan objects with agent assignment and action extraction.
"""

import os
import re
import sys
import unittest

# Add src to the Python path so 'from backend...' imports resolve correctly
# (4 levels up from tests/backend/orchestration/helper/ → src/)
_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Set up environment variables
os.environ.update({
    'APPLICATIONINSIGHTS_CONNECTION_STRING': 'InstrumentationKey=test-key',
    'AZURE_AI_SUBSCRIPTION_ID': 'test-subscription',
    'AZURE_AI_RESOURCE_GROUP': 'test-rg',
    'AZURE_AI_PROJECT_NAME': 'test-project',
})

# Force-clear stale mock entries for the models namespace before importing.
for _k in list(sys.modules.keys()):
    if _k == 'models' or _k.startswith('models.'):
        sys.modules.pop(_k, None)
for _k in ['backend.models.plan_models', 'backend.models']:
    sys.modules.pop(_k, None)

# Import the models first (from backend path)
from backend.models.plan_models import MPlan, MStep, PlanStatus

# Check if models.plan_models is already properly set up (running in full test suite)
_existing_models = sys.modules.get('models.plan_models')
_need_mock = _existing_models is None or not hasattr(_existing_models, 'MPlan')

if _need_mock:
    # Mock models.plan_models with the real classes so relative imports work
    from types import ModuleType
    mock_models_plan_models = ModuleType('plan_models')
    mock_models_plan_models.MPlan = MPlan
    mock_models_plan_models.MStep = MStep
    mock_models_plan_models.PlanStatus = PlanStatus

    if 'models' not in sys.modules:
        sys.modules['models'] = ModuleType('models')
    sys.modules['models.plan_models'] = mock_models_plan_models

# Now import the converter
from backend.orchestration.helper.plan_to_mplan_converter import \
    PlanToMPlanConverter


class TestPlanToMPlanConverter(unittest.TestCase):
    """Test cases for PlanToMPlanConverter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.default_team = ["ResearchAgent", "AnalysisAgent", "ReportAgent"]
        self.converter = PlanToMPlanConverter(
            team=self.default_team,
            task="Test task",
            facts="Test facts"
        )

    def test_init_default_parameters(self):
        """Test PlanToMPlanConverter initialization with default parameters."""
        converter = PlanToMPlanConverter(team=["Agent1", "Agent2"])

        self.assertEqual(converter.team, ["Agent1", "Agent2"])
        self.assertEqual(converter.task, "")
        self.assertEqual(converter.facts, "")
        self.assertEqual(converter.detection_window, 25)
        self.assertEqual(converter.fallback_agent, "MagenticAgent")
        self.assertFalse(converter.enable_sub_bullets)
        self.assertTrue(converter.trim_actions)
        self.assertTrue(converter.collapse_internal_whitespace)

    def test_init_custom_parameters(self):
        """Test PlanToMPlanConverter initialization with custom parameters."""
        converter = PlanToMPlanConverter(
            team=["CustomAgent"],
            task="Custom task",
            facts="Custom facts",
            detection_window=50,
            fallback_agent="DefaultAgent",
            enable_sub_bullets=True,
            trim_actions=False,
            collapse_internal_whitespace=False
        )

        self.assertEqual(converter.team, ["CustomAgent"])
        self.assertEqual(converter.task, "Custom task")
        self.assertEqual(converter.facts, "Custom facts")
        self.assertEqual(converter.detection_window, 50)
        self.assertEqual(converter.fallback_agent, "DefaultAgent")
        self.assertTrue(converter.enable_sub_bullets)
        self.assertFalse(converter.trim_actions)
        self.assertFalse(converter.collapse_internal_whitespace)

    def test_team_lookup_case_insensitive(self):
        """Test that team lookup is case-insensitive."""
        converter = PlanToMPlanConverter(team=["ResearchAgent", "AnalysisAgent"])

        expected_lookup = {
            "researchagent": "ResearchAgent",
            "analysisagent": "AnalysisAgent"
        }
        self.assertEqual(converter._team_lookup, expected_lookup)

    def test_bullet_regex_patterns(self):
        """Test bullet regex pattern matching."""
        test_cases = [
            ("- Simple bullet", True, "", "Simple bullet"),
            ("* Star bullet", True, "", "Star bullet"),
            ("• Unicode bullet", True, "", "Unicode bullet"),
            ("  - Indented bullet", True, "  ", "Indented bullet"),
            ("    * Deep indent", True, "    ", "Deep indent"),
            ("No bullet point", False, None, None),
            ("", False, None, None),
        ]

        for line, should_match, expected_indent, expected_body in test_cases:
            with self.subTest(line=line):
                match = PlanToMPlanConverter.BULLET_RE.match(line)
                if should_match:
                    self.assertIsNotNone(match)
                    self.assertEqual(match.group("indent"), expected_indent)
                    self.assertEqual(match.group("body"), expected_body)
                else:
                    self.assertIsNone(match)

    def test_bold_agent_regex(self):
        """Test bold agent regex pattern matching."""
        test_cases = [
            ("**ResearchAgent** do research", "ResearchAgent", True),
            ("Start **AnalysisAgent** analysis", "AnalysisAgent", True),
            ("**Agent123** task", "Agent123", True),
            ("**Agent_Name** action", "Agent_Name", True),
            ("*SingleAsterik* action", None, False),
            ("**InvalidAgent** action", "InvalidAgent", True),
            ("No bold agent here", None, False),
        ]

        for text, expected_agent, should_match in test_cases:
            with self.subTest(text=text):
                match = PlanToMPlanConverter.BOLD_AGENT_RE.search(text)
                if should_match:
                    self.assertIsNotNone(match)
                    self.assertEqual(match.group(1), expected_agent)
                else:
                    self.assertIsNone(match)

    def test_preprocess_lines(self):
        """Test line preprocessing functionality."""
        plan_text = """
        Line 1

        Line 3 with spaces    

        Line 5
        """

        result = self.converter._preprocess_lines(plan_text)

        expected = ["        Line 1", "        Line 3 with spaces", "        Line 5"]
        self.assertEqual(result, expected)

    def test_preprocess_lines_empty_input(self):
        """Test line preprocessing with empty input."""
        result = self.converter._preprocess_lines("")
        self.assertEqual(result, [])

    def test_preprocess_lines_only_whitespace(self):
        """Test line preprocessing with only whitespace."""
        plan_text = "\n   \n  \n"
        result = self.converter._preprocess_lines(plan_text)
        self.assertEqual(result, [])

    def test_try_bold_agent_success(self):
        """Test successful bold agent extraction."""
        text = "**ResearchAgent** conduct research"
        agent, remaining = self.converter._try_bold_agent(text)

        self.assertEqual(agent, "ResearchAgent")
        self.assertEqual(remaining, "conduct research")

    def test_try_bold_agent_outside_window(self):
        """Test bold agent outside detection window."""
        long_prefix = "a" * 30  # Longer than default detection_window (25)
        text = f"{long_prefix} **ResearchAgent** conduct research"

        agent, remaining = self.converter._try_bold_agent(text)

        self.assertIsNone(agent)
        self.assertEqual(remaining, text)

    def test_try_bold_agent_invalid_agent(self):
        """Test bold agent not in team."""
        text = "**UnknownAgent** do something"
        agent, remaining = self.converter._try_bold_agent(text)

        self.assertIsNone(agent)
        self.assertEqual(remaining, text)

    def test_try_bold_agent_no_bold(self):
        """Test text with no bold agent."""
        text = "ResearchAgent conduct research"
        agent, remaining = self.converter._try_bold_agent(text)

        self.assertIsNone(agent)
        self.assertEqual(remaining, text)

    def test_try_window_agent_success(self):
        """Test successful window agent detection."""
        text = "ResearchAgent should conduct research"
        agent, remaining = self.converter._try_window_agent(text)

        self.assertEqual(agent, "ResearchAgent")
        self.assertEqual(remaining, "should conduct research")

    def test_try_window_agent_case_insensitive(self):
        """Test case-insensitive window agent detection."""
        text = "researchagent should conduct research"
        agent, remaining = self.converter._try_window_agent(text)

        self.assertEqual(agent, "ResearchAgent")
        self.assertEqual(remaining, "should conduct research")

    def test_try_window_agent_beyond_window(self):
        """Test agent name beyond detection window."""
        long_prefix = "a" * 30  # Longer than detection window
        text = f"{long_prefix} ResearchAgent conduct research"

        agent, remaining = self.converter._try_window_agent(text)

        self.assertIsNone(agent)
        self.assertEqual(remaining, text)

    def test_try_window_agent_not_in_team(self):
        """Test agent name not in team."""
        text = "UnknownAgent should do something"
        agent, remaining = self.converter._try_window_agent(text)

        self.assertIsNone(agent)
        self.assertEqual(remaining, text)

    def test_try_window_agent_with_asterisks(self):
        """Test window agent detection removes asterisks."""
        text = "ResearchAgent* should conduct research"
        agent, remaining = self.converter._try_window_agent(text)

        self.assertEqual(agent, "ResearchAgent")
        self.assertEqual(remaining, "should conduct research")

    def test_finalize_action_default_settings(self):
        """Test action finalization with default settings."""
        action = "  conduct   comprehensive   research  "
        result = self.converter._finalize_action(action)

        self.assertEqual(result, "conduct comprehensive research")

    def test_finalize_action_no_trim(self):
        """Test action finalization without trimming."""
        converter = PlanToMPlanConverter(
            team=self.default_team,
            trim_actions=False
        )
        action = "  conduct research  "
        result = converter._finalize_action(action)

        self.assertEqual(result, " conduct research ")

    def test_finalize_action_no_collapse(self):
        """Test action finalization without whitespace collapse."""
        converter = PlanToMPlanConverter(
            team=self.default_team,
            collapse_internal_whitespace=False
        )
        action = "  conduct   comprehensive   research  "
        result = converter._finalize_action(action)

        self.assertEqual(result, "conduct   comprehensive   research")

    def test_finalize_action_no_processing(self):
        """Test action finalization with no processing."""
        converter = PlanToMPlanConverter(
            team=self.default_team,
            trim_actions=False,
            collapse_internal_whitespace=False
        )
        action = "  conduct   comprehensive   research  "
        result = converter._finalize_action(action)

        self.assertEqual(result, action)

    def test_extract_agent_and_action_bold_priority(self):
        """Test agent extraction prioritizes bold agent."""
        body = "**AnalysisAgent** ResearchAgent should analyze"
        agent, action = self.converter._extract_agent_and_action(body)

        self.assertEqual(agent, "AnalysisAgent")
        self.assertEqual(action, "ResearchAgent should analyze")

    def test_extract_agent_and_action_window_fallback(self):
        """Test agent extraction falls back to window search."""
        body = "ResearchAgent should conduct research"
        agent, action = self.converter._extract_agent_and_action(body)

        self.assertEqual(agent, "ResearchAgent")
        self.assertEqual(action, "should conduct research")

    def test_extract_agent_and_action_fallback_agent(self):
        """Test agent extraction uses fallback when no agent found."""
        body = "conduct comprehensive research"
        agent, action = self.converter._extract_agent_and_action(body)

        self.assertEqual(agent, "MagenticAgent")
        self.assertEqual(action, "conduct comprehensive research")

    def test_extract_agent_and_action_custom_fallback(self):
        """Test agent extraction with custom fallback agent."""
        converter = PlanToMPlanConverter(
            team=self.default_team,
            fallback_agent="DefaultAgent"
        )
        body = "conduct research"
        agent, action = converter._extract_agent_and_action(body)

        self.assertEqual(agent, "DefaultAgent")
        self.assertEqual(action, "conduct research")

    def test_parse_simple_plan(self):
        """Test parsing a simple bullet plan."""
        plan_text = """
        - **ResearchAgent** conduct market research
        - **AnalysisAgent** analyze the data
        - **ReportAgent** create final report
        """

        mplan = self.converter.parse(plan_text)

        self.assertIsInstance(mplan, MPlan)
        self.assertEqual(mplan.team, self.default_team)
        self.assertEqual(mplan.user_request, "Test task")
        self.assertEqual(mplan.facts, "Test facts")
        self.assertEqual(len(mplan.steps), 3)

        self.assertEqual(mplan.steps[0].agent, "ResearchAgent")
        self.assertEqual(mplan.steps[0].action, "conduct market research")
        self.assertEqual(mplan.steps[1].agent, "AnalysisAgent")
        self.assertEqual(mplan.steps[1].action, "analyze the data")
        self.assertEqual(mplan.steps[2].agent, "ReportAgent")
        self.assertEqual(mplan.steps[2].action, "create final report")

    def test_parse_mixed_bullet_styles(self):
        """Test parsing with different bullet styles."""
        plan_text = """
        - **ResearchAgent** first task
        * AnalysisAgent second task
        • ReportAgent third task
        """

        mplan = self.converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 3)
        self.assertEqual(mplan.steps[0].agent, "ResearchAgent")
        self.assertEqual(mplan.steps[1].agent, "AnalysisAgent")
        self.assertEqual(mplan.steps[2].agent, "ReportAgent")

    def test_parse_with_sub_bullets(self):
        """Test parsing with sub-bullets enabled."""
        converter = PlanToMPlanConverter(
            team=self.default_team,
            enable_sub_bullets=True
        )

        plan_text = """- **ResearchAgent** main task
  - **AnalysisAgent** sub task
- **ReportAgent** another main task"""

        mplan = converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 3)

        self.assertTrue(hasattr(converter, 'last_step_levels'))
        self.assertEqual(converter.last_step_levels, [0, 1, 0])

    def test_parse_ignores_non_bullet_lines(self):
        """Test parsing ignores non-bullet lines."""
        plan_text = """
        This is a header

        - **ResearchAgent** valid task

        Some explanation text
        Another line

        - **AnalysisAgent** another valid task
        """

        mplan = self.converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 2)
        self.assertEqual(mplan.steps[0].agent, "ResearchAgent")
        self.assertEqual(mplan.steps[1].agent, "AnalysisAgent")

    def test_parse_ignores_empty_actions(self):
        """Test parsing ignores bullets with empty actions."""
        plan_text = """
        - **ResearchAgent**
        - **AnalysisAgent** valid action
        -
        """

        mplan = self.converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 1)
        self.assertEqual(mplan.steps[0].agent, "AnalysisAgent")
        self.assertEqual(mplan.steps[0].action, "valid action")

    def test_parse_empty_plan(self):
        """Test parsing empty plan text."""
        mplan = self.converter.parse("")

        self.assertIsInstance(mplan, MPlan)
        self.assertEqual(len(mplan.steps), 0)
        self.assertEqual(mplan.team, self.default_team)

    def test_parse_no_valid_bullets(self):
        """Test parsing text with no valid bullets."""
        plan_text = """
        This is just text
        No bullets here
        Just explanations
        """

        mplan = self.converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 0)

    def test_parse_with_fallback_agents(self):
        """Test parsing where some bullets use fallback agent."""
        plan_text = """
        - **ResearchAgent** explicit agent task
        - implicit agent task
        - **AnalysisAgent** another explicit task
        """

        mplan = self.converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 3)
        self.assertEqual(mplan.steps[0].agent, "ResearchAgent")
        self.assertEqual(mplan.steps[1].agent, "MagenticAgent")
        self.assertEqual(mplan.steps[2].agent, "AnalysisAgent")

    def test_parse_preserves_mplan_defaults(self):
        """Test parsing preserves MPlan default values when task/facts empty."""
        converter = PlanToMPlanConverter(team=self.default_team)

        plan_text = "- **ResearchAgent** task"
        mplan = converter.parse(plan_text)

        self.assertEqual(mplan.user_request, "")
        self.assertEqual(mplan.facts, "")

    def test_parse_case_sensitivity(self):
        """Test parsing handles case-insensitive agent names."""
        plan_text = """
        - **researchagent** lowercase bold
        - analysisagent mixed case
        - REPORTAGENT uppercase
        """

        mplan = self.converter.parse(plan_text)

        self.assertEqual(len(mplan.steps), 3)
        self.assertEqual(mplan.steps[0].agent, "ResearchAgent")
        self.assertEqual(mplan.steps[1].agent, "AnalysisAgent")


if __name__ == '__main__':
    unittest.main()
