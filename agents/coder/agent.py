import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.memory_store import MemoryStore
from core.safety_sandbox import SafetySandbox
from core.handoff import AgentHandoff
from agents.coder.file_ops import FileOps


GENERATION_SYSTEM_PROMPT = (
    "You are an expert software engineer. Generate clean, production-ready code based on the specification provided. "
    "Follow language-specific best practices, include error handling, use proper typing, and write concise but "
    "readable code. Output ONLY the code and any necessary imports — do not include explanatory prose or disclaimers. "
    "If multiple files are needed, separate them with a '--- filename' delimiter."
)

    MODIFICATION_SYSTEM_PROMPT = (
        "You are an expert software engineer. You will receive a file's contents and instructions for modification. "
        "Output the COMPLETE updated file — not just a diff. No explanations or disclaimers. "
        "Preserve all existing functionality unless the instructions say otherwise. "
        "Follow the same code style, conventions, and patterns already used in the file."
    )

REVIEW_SYSTEM_PROMPT = (
    "You are a senior code reviewer. Review the following code for bugs, security issues, performance problems, "
    "style violations, and correctness. Output a JSON object with keys: 'issues' (list of dicts with 'severity', "
    "'line', 'message', 'suggestion') and 'summary' (overall assessment string). Be thorough but pragmatic."
)


class CodingAgent:
    def __init__(self, llm=None, memory=None, sandbox=None, handoff=None):
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()
        self.sandbox = sandbox or SafetySandbox()
        self.handoff = handoff or AgentHandoff()
        self.file_ops = FileOps()

    def generate(self, spec: str, language: str = "python") -> dict:
        messages = [
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Language: {language}\n\nSpecification:\n{spec}"},
        ]
        try:
            code = self.llm.chat(messages, agent="coder")
            self.memory.store("coder", f"gen:{spec[:50]}", {"language": language, "code": code})
            return {"success": True, "language": language, "code": code}
        except Exception as e:
            return {"success": False, "error": traceback.format_exc()}

    def implement(self, task: str, files: list[dict]) -> dict:
        context = self.handoff.receive_context("coder")
        context_str = ""
        for c in context:
            ctx = c.get("context", {})
            analyses = ctx.get("analyses", {})
            for lens, text in analyses.items():
                context_str += f"\n=== {lens.upper()} ===\n{text[:2000]}\n"

        results = []
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            if not path or not content:
                results.append({"path": path, "success": False, "error": "Missing path or content"})
                continue
            success = self.file_ops.write(path, content)
            results.append({"path": path, "success": success})
            if success:
                self.memory.store("coder", f"write:{path}", content[:500])

        return {
            "task": task,
            "handoff_context_used": bool(context_str),
            "files": results,
            "all_succeeded": all(r["success"] for r in results),
        }

    def modify(self, file_path: str, instructions: str) -> dict:
        content = self.file_ops.read(file_path)
        if content is None:
            return {"success": False, "error": f"Cannot read {file_path}"}
        messages = [
            {"role": "system", "content": MODIFICATION_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"File: {file_path}\n\nCurrent contents:\n```\n{content}\n```"
                f"\n\nInstructions:\n{instructions}"
            )},
        ]
        try:
            new_content = self.llm.chat(messages, agent="coder")
            if self.file_ops.write(file_path, new_content):
                self.memory.store("coder", f"modify:{file_path}", {"before": content[:500], "after": new_content[:500]})
                return {"success": True, "path": file_path}
            else:
                return {"success": False, "error": "Write denied by policy or user"}
        except Exception as e:
            return {"success": False, "error": traceback.format_exc()}

    def review_own_code(self, file_path: str) -> dict:
        content = self.file_ops.read(file_path)
        if content is None:
            return {"error": f"Cannot read {file_path}"}
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": f"File: {file_path}\n\n```\n{content}\n```"},
        ]
        try:
            review_text = self.llm.chat(messages, agent="coder")
            import json
            review = json.loads(review_text)
            self.memory.store("coder", f"review:{file_path}", review)
            return review
        except (json.JSONDecodeError, Exception):
            return {
                "issues": [{"severity": "info", "line": 0, "message": "Could not parse structured review",
                    "suggestion": "Review manually"}],
                "summary": review_text,
            }
