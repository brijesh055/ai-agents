import subprocess, os, json
from datetime import datetime

GIT_DIR = os.getcwd()

def _git(*args, timeout=15):
    try:
        r = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=timeout, cwd=GIT_DIR)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", "git not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"

def is_repo() -> bool:
    rc, _, _ = _git("rev-parse", "--git-dir")
    return rc == 0

def branch() -> str:
    rc, out, _ = _git("branch", "--show-current")
    return out.strip() if rc == 0 else "N/A"

def branches() -> list:
    rc, out, _ = _git("branch")
    if rc != 0:
        return []
    return [b.strip().replace("* ", "") for b in out.split("\n") if b.strip()]

def status() -> str:
    rc, out, _ = _git("status", "--short")
    if rc != 0:
        return "Not a git repository"
    if not out.strip():
        return "Clean working tree"
    lines = out.strip().split("\n")
    staged = [l for l in lines if not l.startswith(" ")]
    unstaged = [l for l in lines if l.startswith(" ")]
    result = f"Branch: {branch()}\n"
    if staged:
        result += f"\nStaged ({len(staged)}):\n" + "\n".join(f"  {l}" for l in staged[:20])
    if unstaged:
        result += f"\nUnstaged ({len(unstaged)}):\n" + "\n".join(f"  {l.strip()}" for l in unstaged[:20])
    if len(lines) > 40:
        result += f"\n  ... ({len(lines) - 40} more)"
    return result

def diff(staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--cached")
    rc, out, _ = _git(*args)
    if rc != 0:
        return ""
    if not out.strip():
        return "No changes"
    lines = out.split("\n")
    return "\n".join(lines[:200]) + ("\n... (truncated)" if len(lines) > 200 else "")

def log(count: int = 10) -> str:
    rc, out, _ = _git("log", f"-{count}", "--oneline", "--decorate")
    return out.strip() if rc == 0 else ""

def commit(message: str) -> dict:
    rc, out, err = _git("commit", "-m", message)
    return {"success": rc == 0, "output": out.strip() or err.strip()}

def auto_commit_message() -> str:
    rc, diff_text, _ = _git("diff", "--cached")
    if rc != 0 or not diff_text.strip():
        rc, diff_text, _ = _git("diff")
    if rc != 0 or not diff_text.strip():
        return "No changes to commit"
    try:
        from core.llm_client import LLMClient
        client = LLMClient()
        msg = client.chat([
            {"role": "system", "content": "Generate a concise git commit message (conventional commits format, max 72 chars). Output ONLY the message."},
            {"role": "user", "content": f"Diff:\n{diff_text[:4000]}"},
        ], agent="git")
        return msg.strip().split("\n")[0][:72]
    except:
        return f"Update {datetime.now().strftime('%Y-%m-%d')}"

def add(paths: list = None):
    if paths:
        for p in paths:
            _git("add", p)
    else:
        _git("add", "-A")

def switch(branch_name: str) -> dict:
    rc, out, err = _git("checkout", branch_name)
    return {"success": rc == 0, "output": out.strip() or err.strip()}

def project_summary() -> str:
    lines = []
    lines.append(f"Branch: {branch()}")
    rc, out, _ = _git("log", "--oneline", "-5")
    if rc == 0:
        lines.append(f"Recent commits:\n{out.strip()}")
    rc, out, _ = _git("remote", "-v")
    if rc == 0 and out.strip():
        for l in out.strip().split("\n"):
            lines.append(f"Remote: {l.split()[1]}")
    rc, out, _ = _git("status", "--short")
    if rc == 0 and out.strip():
        lines.append(f"Changes: {len(out.strip().split(chr(10)))} file(s)")
    return "\n".join(lines)
