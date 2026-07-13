"""Shared knowledge store with auto-logging and search."""
import json
import os
from datetime import datetime


class MemoryStore:
    def __init__(self, path: str = None):
        self.path = path or os.getenv("MEMORY_PATH", os.path.join(os.getcwd(), ".memory_data"))
        os.makedirs(self.path, exist_ok=True)

    def _agent_file(self, agent: str) -> str:
        return os.path.join(self.path, f"{agent}.json")

    def _load_all(self, agent: str) -> list[dict]:
        f = self._agent_file(agent)
        if not os.path.exists(f):
            return []
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save_all(self, agent: str, entries: list[dict]):
        with open(self._agent_file(agent), "w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2, default=str)

    def store(self, agent: str, key: str, value):
        entries = self._load_all(agent)
        entries.append({
            "key": key,
            "value": value,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save_all(agent, entries)

    def retrieve(self, agent: str, key: str):
        entries = self._load_all(agent)
        for e in reversed(entries):
            if e["key"] == key:
                return e["value"]
        return None

    def search(self, query: str) -> list[dict]:
        results = []
        for fname in os.listdir(self.path):
            if not fname.endswith(".json"):
                continue
            agent = fname[:-5]
            entries = self._load_all(agent)
            for e in entries:
                if query.lower() in str(e.get("value", "")).lower() or query.lower() in e.get("key", "").lower():
                    results.append(e)
        return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
