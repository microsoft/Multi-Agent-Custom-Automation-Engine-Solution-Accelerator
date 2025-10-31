import logging
import re
from typing import Iterable, List, Optional

from v3.models.models import MPlan, MStep

logger = logging.getLogger(__name__)


class PlanToMPlanConverter:
    """
    Convert a free-form, bullet-style plan string into an MPlan object.

    Bullet parsing rules:
      1. Recognizes lines starting (optionally with indentation) followed by -, *, or •
      2. Attempts to resolve the agent in priority order:
         a. First bolded token (**AgentName**) if within detection window and in team
         b. Any team agent name appearing (case-insensitive) within the first detection window chars
         c. Fallback agent name (default 'MagenticAgent')
      3. Removes the matched agent token from the action text
      4. Ignores bullet lines whose remaining action is blank

    Notes:
      - This does not mutate MPlan.user_id (caller can assign after parsing).
      - You can supply task text (becomes user_request) and facts text.
      - Optionally detect sub-bullets (indent > 0). If enabled, a `level` integer is
        returned alongside each MStep in an auxiliary `step_levels` list (since the
        current MStep model doesn’t have a level field).

    Example:
        converter = PlanToMPlanConverter(team=["ResearchAgent","AnalysisAgent"])
        mplan = converter.parse(plan_text=raw, task="Analyze Q4", facts="Some facts")

    """

    BULLET_RE = re.compile(r"^(?P<indent>\s*)[-•*]\s+(?P<body>.+)$")
    BOLD_AGENT_RE = re.compile(r"\*\*([A-Za-z0-9_]+)\*\*")
    STRIP_BULLET_MARKER_RE = re.compile(r"^[-•*]\s+")

    def __init__(
        self,
        team: Iterable[str],
        task: str = "",
        facts: str = "",
        detection_window: int = 25,
        fallback_agent: str = "MagenticAgent",
        enable_sub_bullets: bool = False,
        trim_actions: bool = True,
        collapse_internal_whitespace: bool = True,
    ):
        self.team: List[str] = list(team)
        self.task = task
        self.facts = facts
        self.detection_window = detection_window
        self.fallback_agent = fallback_agent
        self.enable_sub_bullets = enable_sub_bullets
        self.trim_actions = trim_actions
        self.collapse_internal_whitespace = collapse_internal_whitespace

        # Map for faster case-insensitive lookups while preserving canonical form
        self._team_lookup = {t.lower(): t for t in self.team}

    # ---------------- Public API ---------------- #

    def parse(self, plan_text: str) -> MPlan:
        """
        Parse the supplied bullet-style plan text into an MPlan.

        Returns:
            MPlan with team, user_request, facts, steps populated.

        Side channel (if sub-bullets enabled):
            self.last_step_levels: List[int] parallel to steps (0 = top, 1 = sub, etc.)
        """
        mplan = MPlan()
        mplan.team = self.team.copy()
        mplan.user_request = self.task or mplan.user_request
        mplan.facts = self.facts or mplan.facts

        lines = self._preprocess_lines(plan_text)

        step_levels: List[int] = []
        for raw_line in lines:
            bullet_match = self.BULLET_RE.match(raw_line)
            if not bullet_match:
                continue  # ignore non-bullet lines entirely

            indent = bullet_match.group("indent") or ""
            body = bullet_match.group("body").strip()

            level = 0
            if self.enable_sub_bullets and indent:
                # Simple heuristic: any indentation => level 1 (could extend to deeper)
                level = 1

            agent, action = self._extract_agent_and_action(body)

            if not action:
                continue

            mplan.steps.append(MStep(agent=agent, action=action))
            if self.enable_sub_bullets:
                step_levels.append(level)

        if self.enable_sub_bullets:
            # Expose levels so caller can correlate (parallel list)
            self.last_step_levels = step_levels  # type: ignore[attr-defined]

        return mplan

    # ---------------- Internal Helpers ---------------- #

    def _preprocess_lines(self, plan_text: str) -> List[str]:
        lines = plan_text.splitlines()
        cleaned: List[str] = []
        for line in lines:
            stripped = line.rstrip()
            if stripped:
                cleaned.append(stripped)
        return cleaned

    def _extract_agent_and_action(self, body: str) -> (str, str):
        """
        Apply bold-first strategy, then window scan fallback.
        Returns (agent, action_text).
        """
        original = body

        # 1. Try bold token
        agent, body_after = self._try_bold_agent(original)
        if agent:
            action = self._finalize_action(body_after)
            return agent, action

        # 2. Try window scan
        agent2, body_after2 = self._try_window_agent(original)
        if agent2:
            action = self._finalize_action(body_after2)
            return agent2, action

        # 3. Fallback
        action = self._finalize_action(original)
        return self.fallback_agent, action

    def _try_bold_agent(self, text: str) -> (Optional[str], str):
        m = self.BOLD_AGENT_RE.search(text)
        if not m:
            return None, text
        if m.start() <= self.detection_window:
            candidate = m.group(1)
            canonical = self._team_lookup.get(candidate.lower())
            if canonical:  # valid agent
                cleaned = text[: m.start()] + text[m.end() :]
                return canonical, cleaned.strip()
        return None, text

    def _try_window_agent(self, text: str) -> (Optional[str], str):
        head_segment = text[: self.detection_window].lower()
        for canonical in self.team:
            if canonical.lower() in head_segment:
                # Remove first occurrence (case-insensitive)
                pattern = re.compile(re.escape(canonical), re.IGNORECASE)
                cleaned = pattern.sub("", text, count=1)
                cleaned = cleaned.replace("*", "")
                return canonical, cleaned.strip()
        return None, text

    def _finalize_action(self, action: str) -> str:
        if self.trim_actions:
            action = action.strip()
        if self.collapse_internal_whitespace:
            action = re.sub(r"\s+", " ", action)
        return action

    # --------------- Convenience (static) --------------- #

    @staticmethod
    def convert(
        plan_text: str,
        team: Iterable[str],
        task: str = "",
        facts: str = "",
        **kwargs,
    ) -> MPlan:
        """
        One-shot convenience method:
            mplan = PlanToMPlanConverter.convert(plan_text, team, task="X")
        """
        return PlanToMPlanConverter(
            team=team,
            task=task,
            facts=facts,
            **kwargs,
        ).parse(plan_text)
