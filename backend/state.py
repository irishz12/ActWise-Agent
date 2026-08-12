from typing import TypedDict


class AgentState(TypedDict):
    user_message: str
    tool_history: list[dict]
    decision_history: list[dict]
    skipped_calls: list[dict]
    decision: str | None
    answer: str | None
    no_progress: int
