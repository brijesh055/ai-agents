"""Docs workflow: Read code -> Generate docs -> Review."""
import os
import sys
import ast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.coder.agent import CodingAgent
from agents.reviewer.agent import ReviewerAgent
from core.handoff import AgentHandoff
from core.task_state import TaskState
from observability.logger import AgentLogger


def _walk_python_files(source_path: str) -> list[str]:
    """Recursively yield all ``.py`` files under *source_path*."""
    py_files: list[str] = []
    source_path = os.path.abspath(source_path)
    if not os.path.isdir(source_path):
        if source_path.endswith(".py") and os.path.isfile(source_path):
            return [source_path]
        return py_files

    for root, _dirs, files in os.walk(source_path):
        for name in files:
            if name.endswith(".py"):
                full = os.path.join(root, name)
                py_files.append(full)
    return sorted(py_files)


def _extract_symbols(file_path: str) -> dict:
    """Parse a Python file and return its classes, functions, and imports."""
    with open(file_path, encoding="utf-8") as fh:
        try:
            tree = ast.parse(fh.read(), filename=file_path)
        except SyntaxError:
            return {"classes": [], "functions": [], "imports": [], "error": "SyntaxError"}

    classes: list[dict] = []
    functions: list[dict] = []
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                {"name": n.name, "lineno": n.lineno}
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append({
                "name": node.name,
                "lineno": node.lineno,
                "docstring": ast.get_docstring(node) or "",
                "methods": methods,
                "bases": [ast.dump(b) for b in node.bases],
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "lineno": node.lineno,
                "docstring": ast.get_docstring(node) or "",
                "args": [arg.arg for arg in node.args.args],
            })
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            else:
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

    return {"classes": classes, "functions": functions, "imports": imports, "error": None}


def _generate_markdown_doc(file_path: str, symbols: dict, source_relative: str) -> str:
    """Generate a Markdown documentation string for a single Python file."""
    lines: list[str] = []
    lines.append(f"# `{source_relative}`\n")

    # Imports
    if symbols.get("imports"):
        lines.append("## Imports\n")
        for imp in symbols["imports"]:
            lines.append(f"- `{imp}`")
        lines.append("")

    # Classes
    if symbols.get("classes"):
        lines.append("## Classes\n")
        for cls in symbols["classes"]:
            anchor = cls["name"].lower()
            lines.append(f"### `{cls['name']}`\n")
            if cls["docstring"]:
                lines.append(f"{cls['docstring']}\n")
            if cls["bases"]:
                lines.append(f"**Bases:** {', '.join(cls['bases'])}\n")
            if cls["methods"]:
                lines.append("Methods:\n")
                for m in cls["methods"]:
                    lines.append(f"- `{m['name']}` (line {m['lineno']})")
                lines.append("")
        lines.append("")

    # Functions
    if symbols.get("functions"):
        lines.append("## Functions\n")
        for fn in symbols["functions"]:
            args_str = ", ".join(fn["args"])
            lines.append(f"### `{fn['name']}({args_str})`\n")
            if fn["docstring"]:
                lines.append(f"{fn['docstring']}\n")
        lines.append("")

    # Full file content link
    lines.append(f"---\n*Source: `{source_relative}`*")

    return "\n".join(lines)


def _write_doc(output_dir: str, relative_path: str, content: str):
    """Write *content* to *output_dir* / *relative_path* with ``.md`` extension."""
    md_name = relative_path.replace(".py", ".md").replace(".", "_").replace("\\", "/")
    md_path = os.path.join(output_dir, md_name)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return md_path


def docs_workflow(source_path: str, output_dir: str = "./docs") -> dict:
    """
    Docs generation pipeline:
    1. Read all Python files in source_path recursively
    2. For each file, extract classes / functions / imports
    3. Generate Markdown documentation for each file
    4. Reviewer checks docs quality
    5. Write docs to output_dir preserving directory structure
    """
    results: dict = {
        "source_path": os.path.abspath(source_path),
        "output_dir": os.path.abspath(output_dir),
        "files_processed": 0,
        "files_written": [],
        "errors": [],
    }
    logger = AgentLogger(agent_name="workflow")
    handoff = AgentHandoff()
    task_state = TaskState()
    source_path_abs = os.path.abspath(source_path)
    source_parent = os.path.dirname(source_path_abs) if os.path.isfile(source_path_abs) else source_path_abs

    logger.info("Starting docs workflow", action="workflow_start", metadata={"source": source_path})

    # ------------------------------------------------------------------
    # Step 1 — Discover Python files
    # ------------------------------------------------------------------
    py_files = _walk_python_files(source_path)
    if not py_files:
        results["error"] = f"No Python files found under {source_path}"
        logger.warn("No Python files found", action="no_files")
        return results

    results["files_found"] = len(py_files)
    logger.info(f"Found {len(py_files)} Python files", action="files_discovered")

    docs_generated: list[dict] = []

    # ------------------------------------------------------------------
    # Step 2 — Extract symbols & generate docs
    # ------------------------------------------------------------------
    for py_file in py_files:
        try:
            # Relative path for output structure
            try:
                rel_path = os.path.relpath(py_file, source_parent)
            except ValueError:
                rel_path = os.path.basename(py_file)

            symbols = _extract_symbols(py_file)
            if symbols.get("error"):
                results["errors"].append({"file": rel_path, "error": symbols["error"]})
                continue

            md_content = _generate_markdown_doc(py_file, symbols, rel_path)

            # Ask LLM to enhance the doc
            try:
                coder = CodingAgent()
                enhanced = coder.generate_docstring(
                    file_path=py_file,
                    symbols=symbols,
                    current_doc=md_content,
                )
                if isinstance(enhanced, str) and enhanced.strip():
                    md_content = enhanced
            except Exception as exc:
                logger.warning(f"LLM enhancement failed for {rel_path}", metadata={"error": str(exc)})

            written_path = _write_doc(output_dir, rel_path, md_content)
            docs_generated.append({
                "source": rel_path,
                "output": written_path,
                "symbols": {
                    "classes": len(symbols.get("classes", [])),
                    "functions": len(symbols.get("functions", [])),
                },
            })
            results["files_written"].append(written_path)
            results["files_processed"] += 1

        except Exception as exc:
            results["errors"].append({"file": py_file, "error": str(exc)})
            logger.error(f"Failed to process {py_file}", metadata={"error": str(exc)})

    task_state.save("docs", {"step": "generate", "status": "done", "docs": docs_generated})
    logger.info("Docs generation complete", action="generate_done", metadata={"count": results["files_processed"]})

    # ------------------------------------------------------------------
    # Step 3 — Reviewer checks overall docs quality
    # ------------------------------------------------------------------
    try:
        reviewer = ReviewerAgent()
        review_text = f"Generated docs for {results['files_processed']} files in {output_dir}"
        review = reviewer.review(review_text, "")
        results["review"] = review
        task_state.save("docs", {"step": "review", "status": "done", "results": review})
        logger.info("Docs review complete", action="review_done")
    except Exception as exc:
        logger.warn("Docs review failed", action="review_failed", metadata={"error": str(exc)})
        results["review_error"] = str(exc)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    task_state.save("docs", {"step": "complete", "status": "done"})
    logger.info("Docs workflow complete", action="workflow_complete", metadata={
        "files_processed": results["files_processed"],
        "errors": len(results["errors"]),
    })

    return results
