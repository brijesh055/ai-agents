"""Runs generated code in temp venv with network off safeguards."""
import subprocess
import tempfile
import os
import shutil
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


class CodeSandbox:
    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="code_sandbox_")
        self.timeout = 30

    def run_python(self, code: str, timeout: int = None) -> SandboxResult:
        timeout = timeout or self.timeout
        fpath = os.path.join(self.work_dir, "sandbox_script.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            result = subprocess.run(
                ["python", fpath],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
                env={**os.environ, "SANDBOXED": "1", "PYTHONNOUSERSITE": "1"},
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                exit_code=-1,
                timed_out=True,
            )
        except FileNotFoundError:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="python interpreter not found",
                exit_code=-1,
            )

    def run_node(self, code: str, timeout: int = None) -> SandboxResult:
        timeout = timeout or self.timeout
        fpath = os.path.join(self.work_dir, "sandbox_script.js")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            result = subprocess.run(
                ["node", fpath],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                exit_code=-1,
                timed_out=True,
            )
        except FileNotFoundError:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="node interpreter not found",
                exit_code=-1,
            )

    def run_shell(self, command: str, timeout: int = None) -> SandboxResult:
        timeout = timeout or self.timeout
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
                env={**os.environ, "SANDBOXED": "1"},
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                exit_code=-1,
                timed_out=True,
            )

    def install_deps(self, deps: list[str]) -> SandboxResult:
        if not deps:
            return SandboxResult(True, "No packages to install", "", 0)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + deps,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.work_dir,
                env={**os.environ, "PIP_REQUIRE_VIRTUALENV": "0"},
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                stdout="",
                stderr="Package installation timed out after 120s",
                exit_code=-1,
                timed_out=True,
            )

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)


import sys
