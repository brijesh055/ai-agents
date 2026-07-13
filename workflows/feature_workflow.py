"""Feature workflow: Research -> Implement -> Test -> Review."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.researcher.agent import ResearcherAgent
from agents.coder.agent import CodingAgent
from agents.web_tester.agent import WebTestingAgent
from agents.reviewer.agent import ReviewerAgent
from core.handoff import AgentHandoff
from core.task_state import TaskState
from observability.logger import AgentLogger


def feature_workflow(
    feature_description: str,
    requirements: str = "",
    repo_path: str = ".",
    target_files: list[str] | None = None,
) -> dict:
    """
    Full feature development pipeline:
    1. Researcher explores requirements and existing codebase for context
    2. Coder implements the feature based on research findings
    3. Reviewer checks implementation quality, completeness, and safety
    4. Tester runs validation tests on the new feature
    """
    results: dict = {}
    logger = AgentLogger(agent_name="workflow")
    handoff = AgentHandoff()
    task_state = TaskState()
    target_files = target_files or []

    logger.info(
        "Starting feature workflow",
        action="workflow_start",
        metadata={"feature": feature_description[:200] if feature_description else ""},
    )

    # ------------------------------------------------------------------
    # Step 1 — Research
    # ------------------------------------------------------------------
    try:
        researcher = ResearcherAgent()
        combined_prompt = f"Feature: {feature_description}"
        if requirements:
            combined_prompt += f"\nRequirements: {requirements}"

        research = researcher.research(combined_prompt)
        results["research"] = research
        task_state.save("feature", {"step": "research", "status": "done", "results": research})
        logger.info("Feature research complete", action="research_done")
    except Exception as exc:
        logger.error("Research step failed", action="research_failed", metadata={"error": str(exc)})
        results["error"] = f"Research failed: {exc}"
        task_state.save("feature", {"step": "research", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 2 — Handoff researcher -> coder
    # ------------------------------------------------------------------
    try:
        handoff.pass_context(
            from_agent="researcher",
            to_agent="coder",
            task=f"Implement feature: {feature_description}",
            context=research,
        )
        task_state.save("feature", {"step": "handoff", "status": "done"})
    except Exception as exc:
        logger.warn("Handoff failed, continuing", action="handoff_failed", metadata={"error": str(exc)})

    # ------------------------------------------------------------------
    # Step 3 — Coder implements feature
    # ------------------------------------------------------------------
    try:
        coder = CodingAgent()

        suggested_files = []
        if isinstance(research, dict):
            suggested_files = research.get("files", research.get("affected_files", []))

        all_targets = list(set(target_files + (suggested_files if isinstance(suggested_files, list) else [])))

        fix = coder.implement(
            instruction=f"Implement feature: {feature_description}",
            file_paths=all_targets,
        )
        results["fix"] = fix
        task_state.save("feature", {"step": "implementation", "status": "done", "results": fix})
        logger.info("Feature implementation complete", action="implement_done")
    except Exception as exc:
        logger.error("Implementation step failed", action="implement_failed", metadata={"error": str(exc)})
        results["error"] = f"Implementation failed: {exc}"
        task_state.save("feature", {"step": "implementation", "status": "failed", "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Step 4 — Reviewer checks implementation
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
        task_state.save("feature", {"step": "review", "status": "done", "results": review})
        logger.info("Feature review complete", action="review_done")
    except Exception as exc:
        logger.error("Review step failed", action="review_failed", metadata={"error": str(exc)})
        results["review_error"] = str(exc)
        task_state.save("feature", {"step": "review", "status": "failed", "error": str(exc)})
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
            test_result = tester.run_tests(target=repo_path)
            results["tested"] = True
            results["test_results"] = test_result
            task_state.save("feature", {"step": "test", "status": "done", "results": test_result})
            logger.info("Feature tests passed", action="test_done")
        except Exception as exc:
            logger.warn("Feature tests failed", action="test_failed", metadata={"error": str(exc)})
            results["tested"] = False
            results["test_error"] = str(exc)
            task_state.save("feature", {"step": "test", "status": "failed", "error": str(exc)})
    else:
        results["tested"] = False
        results["test_skipped"] = "Review found errors; fix before testing"
        logger.info("Feature tests skipped due to review errors", action="test_skipped")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    try:
        summary_data = task_state.summary() if hasattr(task_state, "summary") else results
    except Exception:
        summary_data = results

    task_state.save("feature", {"step": "complete", "status": "done"})
    logger.info("Feature workflow complete", action="workflow_complete", metadata=summary_data)

    return results
