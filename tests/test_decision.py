from pydantic import ValidationError

from backend.decision import AgentDecision


VALID_DECISIONS = ["CONTINUE", "COMPLETE", "CLARIFY", "ABSTAIN"]


for decision in VALID_DECISIONS:
    item = AgentDecision(
        decision=decision,
        reason="A representative reason for this decision.",
    )

    assert item.decision == decision
    assert item.reason == "A representative reason for this decision."

print(f"All {len(VALID_DECISIONS)} valid decisions accepted.")


try:
    AgentDecision(
        decision="INVALID",
        reason="This decision value does not exist.",
    )
except ValidationError:
    pass
else:
    raise AssertionError(
        "AgentDecision accepted an invalid decision value."
    )

print("Invalid decision value correctly rejected.")
