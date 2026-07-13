"""Token usage, time per step, success/failure rates."""

import os
import json
from collections import defaultdict
from .logger import AgentLogger


class MetricsCollector:
    def __init__(self, log_dir: str = None):
        self.logger = AgentLogger(log_dir=log_dir)

    def _read_all(self, agent: str) -> list[dict]:
        return self.logger.get_logs(agent=agent, limit=100000)

    def get_agent_metrics(self, agent: str) -> dict:
        entries = self._read_all(agent)
        if not entries:
            return {
                "agent": agent,
                "call_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "avg_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "actions": {},
            }

        call_count = len(entries)
        error_count = sum(1 for e in entries if e.get("level") == "error")
        error_rate = round(error_count / call_count, 4) if call_count else 0.0

        durations = [e.get("duration_ms", 0) for e in entries if e.get("duration_ms", 0) > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        actions = defaultdict(lambda: {"count": 0, "errors": 0, "total_duration_ms": 0})
        for e in entries:
            key = e.get("action") or e.get("tool") or "unknown"
            actions[key]["count"] += 1
            if e.get("level") == "error":
                actions[key]["errors"] += 1
            actions[key]["total_duration_ms"] += e.get("duration_ms", 0)

        actions_out = {}
        for k, v in actions.items():
            actions_out[k] = {
                "count": v["count"],
                "errors": v["errors"],
                "avg_duration_ms": round(v["total_duration_ms"] / v["count"], 2) if v["count"] else 0.0,
            }

        return {
            "agent": agent,
            "call_count": call_count,
            "error_count": error_count,
            "error_rate": error_rate,
            "avg_duration_ms": round(avg_duration, 2),
            "max_duration_ms": round(max_duration, 2),
            "actions": actions_out,
        }

    def get_all_metrics(self) -> dict[str, dict]:
        agents = self.logger.get_all_agents()
        return {a: self.get_agent_metrics(a) for a in agents}

    def get_errors(self, agent: str = None, limit: int = 50) -> list[dict]:
        if agent:
            entries = self._read_all(agent)
        else:
            entries = []
            for a in self.logger.get_all_agents():
                entries.extend(self._read_all(a))
            entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        errors = [e for e in entries if e.get("level") == "error"]
        return errors[-limit:]

    def get_slow_calls(self, threshold_ms: float = 5000, limit: int = 20) -> list[dict]:
        slow = []
        for a in self.logger.get_all_agents():
            entries = self._read_all(a)
            for e in entries:
                if e.get("duration_ms", 0) > threshold_ms:
                    slow.append(e)
        slow.sort(key=lambda e: e.get("duration_ms", 0), reverse=True)
        return slow[:limit]
