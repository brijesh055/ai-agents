import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.handoff import AgentHandoff
from core.memory_store import MemoryStore
from agents.researcher.agent import ResearcherAgent


class OrchestratorAgent:
    def __init__(self, llm=None, handoff=None, memory=None):
        self.llm = llm or LLMClient()
        self.handoff = handoff or AgentHandoff()
        self.memory = memory or MemoryStore()

    def run_pipeline(self, description: str) -> dict:
        stages_log = []
        results = {}

        # Stage 1 — Research all sectors
        stages_log.append({"name": "research", "status": "running"})
        researcher = ResearcherAgent(llm=self.llm, memory=self.memory)
        research = researcher.research(description)
        results["research"] = research
        sector_count = len(research.get("sectors", {}))
        error_count = len(research.get("errors", {}))
        status = "done" if error_count < sector_count else "failed"
        stages_log[-1]["status"] = status
        stages_log[-1]["output"] = f"{sector_count} sectors analyzed" + (f" ({error_count} errors)" if error_count else "")

        # Stage 2 — Synthesize final report
        if status == "done":
            stages_log.append({"name": "report", "status": "running"})
            report = researcher.synthesize_report(description, research.get("sectors", {}))
            results["report"] = report
            self.handoff.pass_context("researcher", "user", description, {
                "sectors": research.get("sectors", {}),
                "report": report,
            })
            stages_log[-1]["status"] = "done"
            stages_log[-1]["output"] = "final report ready"

        return {
            "description": description,
            "stages": stages_log,
            "results": results,
            "all_passed": all(s["status"] == "done" for s in stages_log),
            "failed_at": None,
        }
