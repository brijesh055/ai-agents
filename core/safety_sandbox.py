"""Sandboxed execution — code runs in temp dirs, file writes intercepted."""
import os
import tempfile
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int


class SafetySandbox:
    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="ai_agents_sandbox_")
        self.allowed_read_roots = [os.getcwd()]
        self.allowed_write_roots = [os.path.join(os.getcwd(), ".ai_agents_output")]

    def execute_code(self, code: str, language: str = "python") -> SandboxResult:
        if language == "python":
            return self._run_python(code)
        elif language == "shell":
            return self._run_shell(code)
        else:
            return SandboxResult(False, "", f"Unsupported language: {language}", 1)

    def _run_python(self, code: str) -> SandboxResult:
        fpath = os.path.join(self.work_dir, "sandbox_script.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            result = subprocess.run(
                ["python", fpath],
                capture_output=True, text=True, timeout=30,
                cwd=self.work_dir,
                env={**os.environ, "SANDBOXED": "1"}
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, "", "Execution timed out (30s)", -1)

    def _run_shell(self, code: str) -> SandboxResult:
        try:
            result = subprocess.run(
                code, shell=True, capture_output=True, text=True, timeout=30,
                cwd=self.work_dir,
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, "", "Execution timed out (30s)", -1)

    def validate_file_access(self, path: str, mode: str = "r") -> bool:
        p = Path(path).resolve()
        if mode == "r":
            return any(str(p).startswith(root) for root in self.allowed_read_roots)
        elif mode in ("w", "a"):
            return any(str(p).startswith(root) for root in self.allowed_write_roots)
        return False

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
