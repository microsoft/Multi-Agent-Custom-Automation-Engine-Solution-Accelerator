"""Custom exceptions for orchestration module."""


class PlanSupersededError(Exception):
    """Raised when a plan's approval wait is cancelled because the user started a new task."""

    def __init__(self, plan_id: str):
        self.plan_id = plan_id
        super().__init__(f"Plan {plan_id} was superseded by a new task")


class PlanTimeoutError(Exception):
    """Raised when user does not approve/reject the plan within the timeout window."""

    def __init__(self, plan_id: str, timeout_seconds: float = 0):
        self.plan_id = plan_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Plan {plan_id} approval timed out after {timeout_seconds}s"
        )
