"""PR review workflow: Review PR -> Suggest fixes -> Apply if approved."""
import os
import subprocess
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.reviewer.agent import ReviewerAgent
from agents.coder.agent import CodingAgent
from core.handoff import AgentHandoff
from core.task_state import TaskState
from observability.logger import AgentLogger


def _fetch_pr_diff(pr_url: str, repo_path: str = ".") -> str:
    """Fetch a PR diff using ``gh pr diff`` or ``git`` CLI."""
    if pr_url:
        pr_number = _parse_pr_number(pr_url)
        if pr_number is not None:
            try:
                result = subprocess.run(
                    ["gh", "pr", "diff", str(pr_number)],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=repo_path,
                    timeout=60,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                logger = AgentLogger(agent_name="workflow")
                logger.warn("gh CLI unavailable or timed out, falling back to git", metadata={"error": str(exc)})

    # Fallback: compare with default branch
    try:
        default_branch = _detect_default_branch(repo_path)
        result = subprocess.run(
            ["git", "diff", f"origin/{default_branch}...HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_path,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout

        # Try simpler diff
        result = subprocess.run(
            ["git", "diff", "HEAD~1"],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_path,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger = AgentLogger(agent_name="workflow")
        logger.warn("git diff failed", metadata={"error": str(exc)})

    return ""


def _parse_pr_number(pr_url: str) -> int | None:
    """Extract PR number from common URL formats."""
    import re
    match = re.search(r"(?:pull|PR|pulls)/(\d+)", pr_url)
    if match:
        return int(match.group(1))
    return None


def _detect_default_branch(repo_path: str) -> str:
    """Detect the default branch name (main / master)."""
    for candidate in ("main", "master"):
        result = subprocess.run(
            ["git", "show-ref", f"refs/heads/{candidate}"],
            capture_output=True, text=True, check=False,
            cwd=repo_path, timeout=10,
        )
        if result.returncode == 0:
            return candidate
    return "main"


def _parse_changed_files(diff_text: str) -> list[str]:
    """Parse diff text to extract changed file paths."""
    files: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            path = line[6:].strip()
            if path and path not in files:
                files.append(path)
    return files


def pr_review_workflow(pr_url: str = "", repo_path: str = ".") -> dict:
    """
    PR review pipeline:
    1. Fetch PR diff (using git or gh CLI)
    2. Reviewer analyzes the diff
    3. If issues found, Coder suggests fixes
    4. Return structured report
    """
    results: dict = {
        "pr_url": pr_url,
        "repo_path": os.path.abspath(repo_path),
    }
    logger = AgentLogger(agent_name="workflow")
    task_state = TaskState()

    logger.info("Starting PR review workflow", action="workflow_start", metadata={"pr": pr_url})

    # ------------------------------------------------------------------
    # Step 1 — Fetch diff
    # ------------------------------------------------------------------
    try:
        diff_text = _fetch_pr_diff(pr_url, repo_path)
        if not diff_text:
            results["error"] = "No diff could be fetched. Check that the PR URL is valid and the repo is up to date."
            logger.error("No diff fetched", action="diff_fetch_failed")
            return results

        results["diff"] = diff_text
        changed_files = _parse_changed_files(diff_text)
        results["changed_files"] = changed_files
        task_state.save("pr_review", {"step": "fetch_diff", "status": "done", "files": changed_files})
        logger.info("Diff fetched", action="diff_fetched", metadata={"files": len(changed_files)})
    except Exception as exc:
        results["error"] = f"Failed to fetch diff: {exc}"
        logger.error("Diff fetch failed", action="diff_fetch_failed", metadata={"error": str(exc)})
        task_state.save("pr_review", {"step": "fetch_diff", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 2 — Reviewer analyzes
    # ------------------------------------------------------------------
    try:
        reviewer = ReviewerAgent()
        review = reviewer.review("\n".join(results.get("changed_files", [])), diff_text)
        results["review"] = review
        task_state.save("pr_review", {"step": "review", "status": "done", "results": review})
        logger.info("PR review complete", action="review_done")
    except Exception as exc:
        logger.error("Review step failed", action="review_failed", metadata={"error": str(exc)})
        results["review_error"] = str(exc)
        task_state.save("pr_review", {"step": "review", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 3 — Coder suggests fixes if issues found
    # ------------------------------------------------------------------
    review_issues = []
    if isinstance(review, dict):
        review_issues = review.get("issues", []) or []

    if review_issues:
        try:
            coder = CodingAgent()
            suggestions = coder.suggest_fixes(
                diff_text=diff_text,
                issues=review_issues,
            )
            results["suggestions"] = suggestions
            task_state.save("pr_review", {"step": "suggest_fixes", "status": "done", "results": suggestions})
            logger.info("Fix suggestions generated", action="suggestions_done")
        except Exception as exc:
            logger.warn("Failed to generate fix suggestions", action="suggestions_failed", metadata={"error": str(exc)})
            results["suggestions_error"] = str(exc)

    task_state.save("pr_review", {"step": "complete", "status": "done"})
    logger.info("PR review workflow complete", action="workflow_complete", metadata=results)

    return results
