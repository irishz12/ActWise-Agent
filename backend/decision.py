from typing import Literal

from pydantic import BaseModel, ConfigDict


DecisionType = Literal[
    "CONTINUE",
    "COMPLETE",
    "CLARIFY",
    "ABSTAIN",
]

ToolAction = Literal[
    "EXECUTE",
    "SKIP",
]


class AgentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    reason: str


class ToolDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ToolAction
    reason: str
