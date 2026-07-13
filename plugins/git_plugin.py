"""Example: PR creation, commit management."""
from .plugin_base import Plugin, PluginContext
from typing import Any
import subprocess
import os


class GitPlugin(Plugin):
    @property
    def name(self) -> str:
        return "git"

    def initialize(self, context: PluginContext):
        self.repo_path = context.config.get("repo_path") or os.getcwd()
        self.github_token = os.getenv("GITHUB_TOKEN", "")

    def execute(self, action: str, params: dict) -> Any:
        if action == "commit":
            return self._commit(params.get("message", ""))
        elif action == "create_branch":
            return self._create_branch(params.get("branch", ""))
        elif action == "create_pr":
            return self._create_pr(params.get("title", ""), params.get("body", ""))
        elif action == "status":
            return self._status()
        raise ValueError(f"Unknown action: {action}")

    def _run_git(self, args: list[str]) -> dict:
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "git command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "git not found on PATH"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _commit(self, message: str) -> dict:
        add_result = self._run_git(["add", "-A"])
        if not add_result["success"]:
            return add_result
        return self._run_git(["commit", "-m", message])

    def _create_branch(self, branch: str) -> dict:
        return self._run_git(["checkout", "-b", branch])

    def _create_pr(self, title: str, body: str) -> dict:
        env = os.environ.copy()
        if self.github_token:
            env["GH_TOKEN"] = self.github_token
        try:
            result = subprocess.run(
                ["gh", "pr", "create", "--title", title, "--body", body],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=30,
                env=env,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            return {"success": False, "error": "gh CLI not found on PATH"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "gh pr create timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _status(self) -> dict:
        return self._run_git(["status"])

    def shutdown(self):
        pass
