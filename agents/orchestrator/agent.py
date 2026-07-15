import sys, os, traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.handoff import AgentHandoff
from core.memory_store import MemoryStore
from agents.researcher.agent import ResearcherAgent
from agents.coder.agent import CodingAgent
from agents.reviewer.agent import ReviewerAgent

STAGES = ["research", "code", "review", "validate"]

class OrchestratorAgent:
    def __init__(self, llm=None, handoff=None, memory=None):
        self.llm = llm or LLMClient()
        self.handoff = handoff or AgentHandoff()
        self.memory = memory or MemoryStore()

    def run_pipeline(self, description: str) -> dict:
        results = {}
        stages_log = []
        failed = None

        # Stage 1 — Research
        stages_log.append({"name": "research", "status": "running"})
        try:
            researcher = ResearcherAgent(llm=self.llm, memory=self.memory)
            research = researcher.research(description)
            results["research"] = research
            research_summary = self._summarize_research(research)
            self.handoff.pass_context("researcher", "coder", description, {
                "analysis": research.get("analyses", {}),
                "summary": research_summary,
            })
            stages_log[-1]["status"] = "done"
            stages_log[-1]["output"] = f"{len(research.get('analyses', {}))} lenses analyzed"
        except Exception as e:
            stages_log[-1]["status"] = "failed"
            stages_log[-1]["error"] = str(e)[:200]
            failed = "research"

        if not failed:
            stages_log.append({"name": "code", "status": "running"})
            try:
                coder = CodingAgent(llm=self.llm, memory=self.memory)
                code_result = coder.generate(description, context=research_summary)
                results["code"] = code_result
                code_text = code_result.get("code", "")
                files = self._extract_files(code_text)
                self.handoff.pass_context("coder", "reviewer", description, {
                    "code": code_text,
                    "files": files,
                    "spec": description,
                })
                stages_log[-1]["status"] = "done"
                stages_log[-1]["output"] = f"{len(files)} file(s) generated" if files else "code generated"
            except Exception as e:
                stages_log[-1]["status"] = "failed"
                stages_log[-1]["error"] = str(e)[:200]
                failed = "code"

        if not failed:
            stages_log.append({"name": "review", "status": "running"})
            try:
                reviewer = ReviewerAgent(llm=self.llm, memory=self.memory)
                review = reviewer.review("(generated)", code=code_text)
                results["review"] = review
                self.handoff.pass_context("reviewer", "tester", description, {
                    "code": code_text,
                    "review": review,
                    "files": files,
                })
                issues = review.get("issues", [])
                errors = sum(1 for i in issues if i.get("severity") == "error")
                warnings = sum(1 for i in issues if i.get("severity") == "warn")
                stages_log[-1]["status"] = "done"
                stages_log[-1]["output"] = f"{errors} errors, {warnings} warnings"
            except Exception as e:
                stages_log[-1]["status"] = "failed"
                stages_log[-1]["error"] = str(e)[:200]
                failed = "review"

        if not failed:
            stages_log.append({"name": "validate", "status": "running"})
            try:
                validation = self._validate_code(code_text)
                results["validation"] = validation
                stages_log[-1]["status"] = "done"
                stages_log[-1]["output"] = "passed" if validation.get("passed") else "failed"
            except Exception as e:
                stages_log[-1]["status"] = "failed"
                stages_log[-1]["error"] = str(e)[:200]
                failed = "validate"

        all_passed = failed is None
        return {
            "description": description,
            "stages": stages_log,
            "results": results,
            "all_passed": all_passed,
            "failed_at": failed,
        }

    def _summarize_research(self, research: dict) -> str:
        analyses = research.get("analyses", {})
        parts = []
        for lens, text in analyses.items():
            if text and not text.startswith("Error"):
                cleaned = text.strip()[:500]
                parts.append(f"=== {lens.upper()} ===\n{cleaned}")
        return "\n\n".join(parts) if parts else "No research data available."

    def _extract_files(self, code_text: str) -> list:
        files = []
        current_file = None
        current_content = []
        for line in code_text.split("\n"):
            if line.startswith("--- ") and line.strip().endswith(("```", "")):
                if current_file:
                    files.append({"path": current_file, "content": "\n".join(current_content)})
                parts = line.strip().split(" ", 1)
                current_file = parts[1] if len(parts) > 1 else None
                current_file = current_file.rstrip("`").strip() if current_file else None
                current_content = []
            else:
                current_content.append(line)
        if current_file:
            files.append({"path": current_file, "content": "\n".join(current_content)})
        if not files:
            files.append({"path": "generated", "content": code_text})
        return files

    def _validate_code(self, code_text: str) -> dict:
        files = self._extract_files(code_text)
        issues = []
        for f in files:
            path = f["path"]
            content = f["content"]
            if path.endswith(".py"):
                try:
                    compile(content, path, "exec")
                except SyntaxError as e:
                    issues.append({"file": path, "line": e.lineno, "message": str(e)})
        return {"passed": len(issues) == 0, "files_checked": len(files), "issues": issues}
