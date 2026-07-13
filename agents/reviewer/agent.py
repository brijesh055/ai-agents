import sys
import os
import re
import json
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.memory_store import MemoryStore
from core.handoff import AgentHandoff
from agents.reviewer.rules import get_rules, get_rule


REVIEW_SYSTEM_PROMPT = (
    "You are a senior code reviewer. Analyze the provided code and return a JSON object with the following structure:\n"
    '{\n  "issues": [\n    {\n      "severity": "error" | "warn" | "info",\n      "line": <int or null>,\n'
    '      "message": "<description of the issue>",\n      "suggestion": "<how to fix it>"\n    }\n  ],\n'
    '  "summary": "<overall assessment of code quality, 2-3 sentences>"\n}\n'
    "Focus on: correctness, security, performance, maintainability, style consistency, and error handling. "
    "Be thorough but practical — don't nitpick trivial issues. Return ONLY valid JSON."
)

PR_REVIEW_SYSTEM_PROMPT = (
    "You are a senior engineer reviewing a pull request diff. Analyze the changes and return a JSON object:\n"
    '{\n  "issues": [{"severity": "error"|"warn"|"info", "file": "<path>", "line": <int|null>,\n'
    '    "message": "...", "suggestion": "..."}],\n'
    '  "summary": "<overall assessment>",\n'
    '  "approved": <bool>,\n'
    '  "changes_requested": <bool>\n}\n'
    "Return ONLY valid JSON."
)


class ReviewerAgent:
    def __init__(self, llm=None, memory=None, handoff=None):
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()
        self.handoff = handoff or AgentHandoff()

    def review(self, file_path: str, code: str = None) -> dict:
        if code is None:
            if not os.path.exists(file_path):
                return {"issues": [], "summary": f"File not found: {file_path}"}
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this code from {file_path}:\n\n```\n{code}\n```"},
        ]
        review_text = ""
        try:
            review_text = self.llm.chat(messages, agent="reviewer")
            review = json.loads(review_text)
        except json.JSONDecodeError:
            review = {
                "issues": [{"severity": "info", "line": 0, "message": "LLM review parsing failed",
                    "suggestion": "Run a manual review"}],
                "summary": str(review_text)[:200],
            }
        except Exception:
            review = {
                "issues": [{"severity": "info", "line": 0, "message": "LLM review failed",
                            "suggestion": "Check LLM connection"}],
                "summary": "Review could not be completed due to an error",
            }

        rule_issues = self._check_rules_on_code(code, file_path)
        review.setdefault("issues", [])
        review["issues"].extend(rule_issues)

        self.memory.store("reviewer", f"review:{file_path}", review)
        return review

    def review_pr(self, diff_text: str) -> dict:
        messages = [
            {"role": "system", "content": PR_REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this PR diff:\n\n```diff\n{diff_text}\n```"},
        ]
        try:
            review_text = self.llm.chat(messages, agent="reviewer")
            review = json.loads(review_text)
        except (json.JSONDecodeError, Exception):
            review = {
                "issues": [],
                "summary": review_text if isinstance(review_text, str) else "Could not parse review",
                "approved": False,
                "changes_requested": True,
            }

        self.memory.store("reviewer", f"pr:{diff_text[:50]}", review)
        return review

    def suggest_fixes(self, file_path: str, issues: list[dict]) -> dict:
        code = None
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        if not code:
            return {"success": False, "error": f"Cannot read {file_path}"}

        issues_text = json.dumps(issues, indent=2)
        messages = [
            {"role": "system", "content": "You are a senior engineer. Given a file and a list of issues,
                output the COMPLETE fixed file content that resolves all issues. Preserve all other code exactly."},
            {"role": "user", "content": (
                f"File: {file_path}\n\nCurrent code:\n```\n{code}\n```\n\n"
                f"Issues to fix:\n{issues_text}\n\n"
                "Output ONLY the complete fixed code, no explanation."
            )},
        ]
        try:
            fixed_code = self.llm.chat(messages, agent="reviewer")
            return {"success": True, "path": file_path, "fixed_code": fixed_code}
        except Exception as e:
            return {"success": False, "error": traceback.format_exc()}

    def check_rules(self, file_path: str, rules: list[str]) -> list[dict]:
        if not os.path.exists(file_path):
            return [{"rule": "N/A", "severity": "error", "message": f"File not found: {file_path}"}]
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        results = []
        for rule_name in rules:
            rule = get_rule(rule_name)
            if rule is None:
                results.append({"rule": rule_name, "severity": "warn", "message": f"Unknown rule: {rule_name}"})
                continue
            pattern = rule.get("pattern")
            if pattern:
                matches = list(re.finditer(pattern, code, re.IGNORECASE))
                for m in matches:
                    line_num = code[:m.start()].count("\n") + 1
                    results.append({
                        "rule": rule_name,
                        "severity": rule["severity"],
                        "line": line_num,
                        "message": rule["description"],
                    })
            else:
                lines = code.split("\n")
                for i, line in enumerate(lines, 1):
                    if rule_name == "function_docstrings":
                        stripped = line.strip()
                        if stripped.startswith("def ") and stripped.endswith(":"):
                            next_line = lines[i] if i < len(lines) else ""
                            next_stripped = next_line.strip()
                            if not (next_stripped.startswith('"') or next_stripped.startswith("'''")):
                                func_name = stripped.split("(")[0].replace("def ", "").strip()
                                results.append({
                                    "rule": rule_name,
                                    "severity": rule["severity"],
                                    "line": i,
                                    "message": f"Function '{func_name}' is missing a docstring.",
                                })
                    elif rule_name == "max_line_length":
                        if len(line.rstrip("\n")) > 120:
                            results.append({
                                "rule": rule_name,
                                "severity": rule["severity"],
                                "line": i,
                                "message": f"Line exceeds 120 characters ({len(line.rstrip())} chars).",
                            })

        self.memory.store("reviewer", f"rules:{file_path}", results)
        return results

    def _check_rules_on_code(self, code: str, file_path: str) -> list[dict]:
        results = []
        all_rules = get_rules()
        for rule in all_rules:
            if rule["name"] in ("max_line_length", "function_docstrings"):
                pattern = rule.get("pattern")
                if pattern:
                    matches = re.finditer(pattern, code, re.IGNORECASE)
                    for m in matches:
                        line_num = code[:m.start()].count("\n") + 1
                        results.append({
                            "rule": rule["name"],
                            "severity": rule["severity"],
                            "line": line_num,
                            "message": rule["description"],
                        })
                else:
                    lines = code.split("\n")
                    for i, line in enumerate(lines, 1):
                        if rule["name"] == "function_docstrings":
                            stripped = line.strip()
                            if stripped.startswith("def ") and stripped.endswith(":"):
                                next_line = lines[i] if i < len(lines) else ""
                                next_stripped = next_line.strip()
                                if not (next_stripped.startswith('"') or next_stripped.startswith("'''")):
                                    func_name = stripped.split("(")[0].replace("def ", "").strip()
                                    results.append({
                                        "rule": rule["name"],
                                        "severity": rule["severity"],
                                        "line": i,
                                        "message": f"Function '{func_name}' is missing a docstring.",
                                    })
                        elif rule["name"] == "max_line_length":
                            if len(line.rstrip("\n")) > 120:
                                results.append({
                                    "rule": rule["name"],
                                    "severity": rule["severity"],
                                    "line": i,
                                    "message": f"Line exceeds 120 characters ({len(line.rstrip())} chars).",
                                })
            else:
                pattern = rule.get("pattern")
                if not pattern:
                    continue
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for m in matches:
                    line_num = code[:m.start()].count("\n") + 1
                    results.append({
                        "rule": rule["name"],
                        "severity": rule["severity"],
                        "line": line_num,
                        "message": rule["description"],
                    })

        return results
