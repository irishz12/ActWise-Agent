from backend.decision import AgentDecision


decisions = [
    AgentDecision(
        decision="CONTINUE",
        reason="The premium summary is still required.",
    ),
    AgentDecision(
        decision="COMPLETE",
        reason="Duplicate IDs and average premium are available.",
    ),
    AgentDecision(
        decision="CLARIFY",
        reason="The user did not specify which column to analyze.",
    ),
    AgentDecision(
        decision="ABSTAIN",
        reason="The requested file does not exist in the workspace.",
    ),
]

for item in decisions:
    print(item.model_dump())
