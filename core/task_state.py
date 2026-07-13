"""Checkpoint/resume — serializes agent state so a crash picks up where it left off."""
import json
import os
from datetime import datetime


class TaskState:
    def __init__(self, state_dir: str = None):
        self.state_dir = state_dir or os.path.join(os.getcwd(), ".ai_agents_state")
        os.makedirs(self.state_dir, exist_ok=True)

    def _path(self, task_id: str) -> str:
        return os.path.join(self.state_dir, f"{task_id}.json")

    def save(self, task_id: str, state: dict):
        state["_updated"] = datetime.utcnow().isoformat()
        with open(self._path(task_id), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)

    def load(self, task_id: str) -> dict | None:
        p = self._path(task_id)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def list(self) -> list[str]:
        return [f[:-5] for f in os.listdir(self.state_dir) if f.endswith(".json")]

    def delete(self, task_id: str):
        p = self._path(task_id)
        if os.path.exists(p):
            os.remove(p)

    def exists(self, task_id: str) -> bool:
        return os.path.exists(self._path(task_id))
