import sys, os, traceback, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.memory_store import MemoryStore
from agents.researcher.prompts import SECTORS, SECTORS_ORDER, SYNTHESIS_PROMPT


GENERAL_PROMPT = (
    "You are a knowledgeable AI assistant. Answer the user's question clearly and concisely. "
    "Be accurate, cite facts, and keep responses well-structured but brief. "
    "If the question is ambiguous, ask for clarification. Do not over-analyze simple questions."
)

CLASSIFY_PROMPT = (
    "Classify this query into exactly one category:\n"
    "- 'general' — general knowledge, facts, definitions, explanations, casual chat, opinions\n"
    "- 'deep' — building/developing/creating a project, app, system, feature, architecture, or requiring multi-domain technical analysis\n\n"
    "Output ONLY the word: general or deep"
)


class ResearcherAgent:
    def __init__(self, llm: LLMClient = None, memory: MemoryStore = None):
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()

    def _classify(self, topic: str) -> str:
        try:
            msg = self.llm.chat([
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": topic},
            ], agent="researcher")
            msg = msg.strip().lower()[:10]
            return "deep" if msg == "deep" else "general"
        except:
            return "deep"

    def research(self, topic: str) -> dict:
        if not topic or not topic.strip():
            return {"error": "Topic cannot be empty"}

        query_type = self._classify(topic)
        if query_type == "general":
            return self._answer_general(topic)

        return self._deep_research(topic)

    def _answer_general(self, topic: str) -> dict:
        try:
            answer = self.llm.chat([
                {"role": "system", "content": GENERAL_PROMPT},
                {"role": "user", "content": topic},
            ], agent="researcher")
            self.memory.store("researcher", f"{topic}:general", answer)
            return {"topic": topic, "type": "general", "answer": answer, "sectors": {}}
        except Exception as e:
            return {"topic": topic, "type": "general", "error": str(e)}

    def _deep_research(self, topic: str) -> dict:
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

        output = {"topic": topic, "type": "deep", "sectors": results}
        if errors:
            output["errors"] = errors
        return output

    def synthesize_report(self, topic: str, sectors: dict) -> str:
        if not sectors:
            return ""
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
