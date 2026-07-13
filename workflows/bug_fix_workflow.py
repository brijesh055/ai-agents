"""Bug fix workflow: Researcher finds context -> Coder fixes -> Tester verifies -> Reviewer approves."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.researcher.agent import ResearcherAgent
from agents.coder.agent import CodingAgent
from agents.web_tester.agent import WebTestingAgent
from agents.reviewer.agent import ReviewerAgent
from core.handoff import AgentHandoff
from core.task_state import TaskState
from observability.logger import AgentLogger


def bug_fix_workflow(
    issue_url: str = "",
    issue_description: str = "",
    repo_path: str = ".",
) -> dict:
    """
    Full bug fix pipeline:
    1. Researcher analyzes the bug (reads issue, searches for root cause)
    2. Passes findings to Coder via handoff
    3. Coder implements the fix
    4. Web Tester runs a verification test
    5. Reviewer checks the fix quality
    """
    results: dict = {}
    logger = AgentLogger(agent_name="workflow")
    handoff = AgentHandoff()
    task_state = TaskState()

    issue_text = issue_description or issue_url or "unknown"

    logger.info(
        "Starting bug fix workflow",
        action="workflow_start",
        metadata={"issue": issue_text},
    )

    # ------------------------------------------------------------------
    # Step 1 — Research
    # ------------------------------------------------------------------
    try:
        researcher = ResearcherAgent()
        research = researcher.research(f"Bug: {issue_text}")
        results["research"] = research
        task_state.save("bug_fix", {"step": "research", "status": "done", "results": research})
        logger.info("Research complete", action="research_done")
    except Exception as exc:
        logger.error("Research step failed", action="research_failed", metadata={"error": str(exc)})
        results["error"] = f"Research failed: {exc}"
        task_state.save("bug_fix", {"step": "research", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 2 — Handoff researcher -> coder
    # ------------------------------------------------------------------
    try:
        handoff.pass_context(
            from_agent="researcher",
            to_agent="coder",
            task=f"Fix bug: {issue_text}",
            context=research,
        )
        task_state.save("bug_fix", {"step": "handoff", "status": "done"})
    except Exception as exc:
        logger.warn("Handoff failed, continuing", action="handoff_failed", metadata={"error": str(exc)})

    # ------------------------------------------------------------------
    # Step 3 — Coder implements fix
    # ------------------------------------------------------------------
    try:
        coder = CodingAgent()
        files_to_fix: list[str] = []

        if isinstance(research, dict):
            files_to_fix = research.get("files", research.get("affected_files", []))

        fix = coder.implement(
            instruction=f"Fix this bug: {issue_text}",
            file_paths=files_to_fix if isinstance(files_to_fix, list) else [],
        )
        results["fix"] = fix
        task_state.save("bug_fix", {"step": "implementation", "status": "done", "results": fix})
        logger.info("Implementation complete", action="implement_done")
    except Exception as exc:
        logger.error("Implementation step failed", action="implement_failed", metadata={"error": str(exc)})
        results["error"] = f"Implementation failed: {exc}"
        task_state.save("bug_fix", {"step": "implementation", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 4 — Reviewer checks fix
    # ------------------------------------------------------------------
    try:
        reviewer = ReviewerAgent()
        file_path = ""
        content = ""

        if isinstance(fix, dict):
            file_path = fix.get("file_path", "")
            content = fix.get("content", "")

        review = reviewer.review(file_path, content)
        results["review"] = review
        task_state.save("bug_fix", {"step": "review", "status": "done", "results": review})
        logger.info("Review complete", action="review_done")
    except Exception as exc:
        logger.error("Review step failed", action="review_failed", metadata={"error": str(exc)})
        results["review_error"] = str(exc)
        results["tested"] = False
        task_state.save("bug_fix", {"step": "review", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 5 — Test if review passes
    # ------------------------------------------------------------------
    review_issues = []
    if isinstance(review, dict):
        review_issues = review.get("issues", []) or []

    has_errors = any(
        isinstance(i, dict) and i.get("severity") == "error"
        for i in review_issues
    )

    if not has_errors:
        try:
            tester = WebTestingAgent()
            test_result = tester.run_tests(target=file_path or repo_path)
            results["tested"] = True
            results["test_results"] = test_result
            task_state.save("bug_fix", {"step": "test", "status": "done", "results": test_result})
            logger.info("Tests passed", action="test_done")
        except Exception as exc:
            logger.warn("Tests failed", action="test_failed", metadata={"error": str(exc)})
            results["tested"] = False
            results["test_error"] = str(exc)
            task_state.save("bug_fix", {"step": "test", "status": "failed", "error": str(exc)})
    else:
        results["tested"] = False
        results["test_skipped"] = "Review found errors; fix before testing"
        logger.info("Tests skipped due to review errors", action="test_skipped")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    try:
        summary_data = task_state.summary() if hasattr(task_state, "summary") else results
    except Exception:
        summary_data = results

    task_state.save("bug_fix", {"step": "complete", "status": "done"})
    logger.info("Bug fix workflow complete", action="workflow_complete", metadata=summary_data)

    return results
