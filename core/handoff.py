"""Agent-to-agent handoff with typed contracts."""
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class HandoffContract:
    from_agent: str
    to_agent: str
    task: str
    context: dict[str, Any]
    artifacts: list[dict[str, Any]]
    timestamp: str = ""


class AgentHandoff:
    def __init__(self, handoff_dir: str = None):
        self.handoff_dir = handoff_dir or os.path.join(os.getcwd(), ".ai_agents_handoffs")
        os.makedirs(self.handoff_dir, exist_ok=True)

    def pass_context(self, from_agent: str, to_agent: str, task: str, context: dict, artifacts: list = None):
        contract = HandoffContract(
            from_agent=from_agent,
            to_agent=to_agent,
            task=task,
            context=context,
            artifacts=artifacts or [],
            timestamp=datetime.utcnow().isoformat(),
        )
        fname = f"{to_agent}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.json"
        with open(os.path.join(self.handoff_dir, fname), "w", encoding="utf-8") as f:
            json.dump(asdict(contract), f, indent=2, default=str)

    def receive_context(self, agent: str) -> list[dict]:
        results = []
        for fname in sorted(os.listdir(self.handoff_dir)):
            if not fname.startswith(f"{agent}_") or not fname.endswith(".json"):
                continue
            with open(os.path.join(self.handoff_dir, fname), "r", encoding="utf-8") as f:
                results.append(json.load(f))
        return results

    def clear(self, agent: str = None):
        for fname in os.listdir(self.handoff_dir):
            if not fname.endswith(".json"):
                continue
            if agent and not fname.startswith(f"{agent}_"):
                continue
            os.remove(os.path.join(self.handoff_dir, fname))
