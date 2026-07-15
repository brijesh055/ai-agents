import sys, os, traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.memory_store import MemoryStore
from agents.researcher.prompts import SECTORS, SECTORS_ORDER, SYNTHESIS_PROMPT


class ResearcherAgent:
    def __init__(self, llm: LLMClient = None, memory: MemoryStore = None):
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()

    def research(self, topic: str) -> dict:
        if not topic or not topic.strip():
            return {"error": "Topic cannot be empty"}
        results = {}
        errors = {}
        for sector in SECTORS_ORDER:
            system_prompt = SECTORS[sector]
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this topic thoroughly and produce your sector analysis:\n\n{topic}"},
                ]
                analysis = self.llm.chat(messages, agent="researcher")
                results[sector] = analysis
                self.memory.store("researcher", f"{topic}:{sector}", analysis)
            except Exception as e:
                errors[sector] = str(e)
                results[sector] = f"Error analyzing {sector}: {traceback.format_exc()}"

        output = {"topic": topic, "sectors": results}
        if errors:
            output["errors"] = errors
        return output

    def synthesize_report(self, topic: str, sectors: dict) -> str:
        parts = []
        for sector in SECTORS_ORDER:
            text = sectors.get(sector, "")
            if text and not text.startswith("Error"):
                parts.append(f"=== {sector.upper()} ===\n{text[:2000]}")
        if not parts:
            return "No sector data available to synthesize."
        sector_text = "\n\n".join(parts)
        messages = [
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": f"Topic: {topic}\n\nDomain analyses:\n{sector_text}"},
        ]
        report = self.llm.chat(messages, agent="researcher")
        self.memory.store("researcher", f"{topic}:report", report)
        return report
