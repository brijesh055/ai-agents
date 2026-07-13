"""Replay an agent's full decision trace."""

import json
import os
from collections import defaultdict
from .logger import AgentLogger


class TraceViewer:
    def __init__(self, log_dir: str = None):
        self.logger = AgentLogger(log_dir=log_dir)

    def get_trace(self, agent: str, task_id: str = None) -> list[dict]:
        entries = self.logger.get_logs(agent=agent, limit=10000)
        if task_id:
            entries = [
                e
                for e in entries
                if e.get("metadata", {}).get("task_id") == task_id
            ]
        return entries

    def format_trace(self, agent: str, task_id: str = None) -> str:
        entries = self.get_trace(agent, task_id)
        lines = []
        for e in entries:
            ts = e.get("timestamp", "")
            try:
                ts_display = ts[11:19]
            except (IndexError, TypeError):
                ts_display = ts
            level = e.get("level", "INFO").upper()
            agent_name = e.get("agent", agent)
            msg = e.get("message", "")
            parts = [f"[{ts_display}] {level:5s} {agent_name}  {msg}"]

            action = e.get("action", "")
            tool = e.get("tool", "")
            duration = e.get("duration_ms", 0)
            details = []
            if action:
                details.append(f"action: {action}")
            if tool:
                details.append(f"tool: {tool}")
            if duration:
                details.append(f"{int(duration)}ms")
            if details:
                parts.append(f"  ({', '.join(details)})")
            lines.append("".join(parts))
        return "\n".join(lines)

    def summary(self, agent: str) -> dict:
        entries = self.logger.get_logs(agent=agent, limit=100000)
        if not entries:
            return {
                "agent": agent,
                "total_calls": 0,
                "error_count": 0,
                "avg_duration_ms": 0.0,
                "actions": {},
            }

        error_count = sum(1 for e in entries if e.get("level") == "error")
        durations = [e.get("duration_ms", 0) for e in entries if e.get("duration_ms", 0) > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        actions = defaultdict(int)
        for e in entries:
            action = e.get("action") or e.get("tool") or "unknown"
            actions[action] += 1

        return {
            "agent": agent,
            "total_calls": len(entries),
            "error_count": error_count,
            "avg_duration_ms": round(avg_duration, 2),
            "actions": dict(actions),
        }
