"""Structured logging — agent name, timestamp, action, tool calls."""

import json
import os
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Any


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class LogEntry:
    timestamp: str = ""
    agent: str = ""
    level: str = "info"
    message: str = ""
    action: str = ""
    tool: str = ""
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class AgentLogger:
    def __init__(self, log_dir: str = None, agent_name: str = "unknown"):
        self.log_dir = log_dir or os.path.join(os.getcwd(), ".ai_agents_logs")
        self.agent_name = agent_name
        os.makedirs(self.log_dir, exist_ok=True)

    def _log(
        self,
        level: LogLevel,
        message: str,
        action: str = "",
        tool: str = "",
        duration_ms: float = 0,
        metadata: dict = None,
    ):
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            agent=self.agent_name,
            level=level.value,
            message=message,
            action=action,
            tool=tool,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        filename = os.path.join(self.log_dir, f"{self.agent_name}.jsonl")
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)

    def warn(self, message: str, **kwargs):
        self._log(LogLevel.WARN, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)

    def get_logs(self, agent: str = None, limit: int = 100) -> list[dict]:
        agent = agent or self.agent_name
        filename = os.path.join(self.log_dir, f"{agent}.jsonl")
        if not os.path.exists(filename):
            return []
        entries = []
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-limit:]

    def get_all_agents(self) -> list[str]:
        agents = []
        if not os.path.isdir(self.log_dir):
            return agents
        for fname in os.listdir(self.log_dir):
            if fname.endswith(".jsonl"):
                agents.append(fname[: -len(".jsonl")])
        return sorted(agents)
