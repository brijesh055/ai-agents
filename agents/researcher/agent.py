import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.memory_store import MemoryStore
from agents.researcher.prompts import LENSES


class ResearcherAgent:
    def __init__(self, llm: LLMClient = None, memory: MemoryStore = None):
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()

    def research(self, topic: str) -> dict:
        if not topic or not topic.strip():
            return {"error": "Topic cannot be empty"}
        results = {}
        errors = {}
        for lens, system_prompt in LENSES.items():
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this topic thoroughly: {topic}"},
                ]
                analysis = self.llm.chat(messages, agent="researcher")
                results[lens] = analysis
                self.memory.store("researcher", f"{topic}:{lens}", analysis)
            except Exception as e:
                errors[lens] = str(e)
                results[lens] = f"Error analyzing {lens}: {traceback.format_exc()}"
        output = {"topic": topic, "analyses": results}
        if errors:
            output["errors"] = errors
        return output
