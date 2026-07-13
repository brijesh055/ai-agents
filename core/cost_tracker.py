"""Cost tracking — per-call, per-agent, per-session."""
import json
import os
from datetime import datetime


RATES = {
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "qwen2.5:7b": {"input": 0, "output": 0},
    "default": {"input": 0, "output": 0},
}


class CostTracker:
    def __init__(self, log_path: str = None):
        self.log_path = log_path or os.path.join(os.getcwd(), ".ai_agents_costs.jsonl")
        self.session_calls = []

    def log_call(self, agent: str, model: str, tokens_in: int, tokens_out: int):
        rate = RATES.get(model, RATES["default"])
        cost = (tokens_in * rate["input"]) + (tokens_out * rate["output"])
        entry = {
            "agent": agent,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": round(cost, 6),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.session_calls.append(entry)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_session_cost(self) -> float:
        return round(sum(c["cost"] for c in self.session_calls), 4)

    def get_agent_cost(self, agent: str) -> float:
        return round(
            sum(c["cost"] for c in self.session_calls if c["agent"] == agent), 4
        )

    def get_session_tokens(self) -> dict:
        total_in = sum(c["tokens_in"] for c in self.session_calls)
        total_out = sum(c["tokens_out"] for c in self.session_calls)
        return {"input": total_in, "output": total_out, "total": total_in + total_out}

    def summary(self) -> dict:
        return {
            "session_cost": self.get_session_cost(),
            "tokens": self.get_session_tokens(),
            "calls": len(self.session_calls),
        }

    def reset(self):
        self.session_calls = []
