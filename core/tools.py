import os, subprocess, json, glob as glob_mod
from pathlib import Path

TOOLS = []

def tool(name, description, parameters):
    def decorator(func):
        func._tool_meta = {"name": name, "description": description, "parameters": parameters}
        TOOLS.append(func)
        return func
    return decorator

def get_tool_schemas():
    schemas = []
    for fn in TOOLS:
        meta = fn._tool_meta
        schemas.append({
            "name": meta["name"],
            "description": meta["description"],
            "parameters": meta["parameters"],
        })
    return schemas

def execute_tool(name: str, args: dict) -> str:
    for fn in TOOLS:
        if fn._tool_meta["name"] == name:
            try:
                result = fn(**args)
                if isinstance(result, str):
                    return result
                return json.dumps(result, indent=2, default=str)
            except Exception as e:
                return f"Error executing {name}: {e}"
    return f"Unknown tool: {name}"

@tool("read_file", "Read contents of a file", {"type": "object", "properties": {
    "path": {"type": "string", "description": "Absolute or relative file path"},
}, "required": ["path"]})
def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"
    content = p.read_text(encoding="utf-8")
    lines = content.split("\n")
    return f"File: {path} ({len(lines)} lines, {len(content)} chars)\n```\n{content[:5000]}```" + ("\n... (truncated)" if len(content) > 5000 else "")

@tool("write_file", "Write content to a file (creates parent dirs if needed)", {"type": "object", "properties": {
    "path": {"type": "string", "description": "File path to write"},
    "content": {"type": "string", "description": "Content to write"},
}, "required": ["path", "content"]})
def write_file(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"

@tool("run_command", "Run a shell command and get output", {"type": "object", "properties": {
    "command": {"type": "string", "description": "Shell command to execute"},
    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
}, "required": ["command"]})
def run_command(command: str, timeout: int = 30) -> str:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd())
        out = r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout
        err = r.stderr[-1000:] if len(r.stderr) > 1000 else r.stderr
        result = f"Exit code: {r.returncode}\n"
        if out:
            result += f"STDOUT:\n{out}\n"
        if err:
            result += f"STDERR:\n{err}\n"
        return result.strip()
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

@tool("list_files", "List files in a directory", {"type": "object", "properties": {
    "path": {"type": "string", "description": "Directory path", "default": "."},
    "pattern": {"type": "string", "description": "Optional glob filter (e.g. *.py)"},
}, "required": []})
def list_files(path: str = ".", pattern: str = "") -> str:
    p = Path(path)
    if not p.is_dir():
        return f"Not a directory: {path}"
    if pattern:
        items = list(p.glob(pattern))
    else:
        items = list(p.iterdir())
    lines = []
    for item in sorted(items):
        suffix = "/" if item.is_dir() else ""
        lines.append(f"  {item.name}{suffix}")
    return f"Listing {path}/ ({len(items)} items)\n" + "\n".join(lines[:50]) + ("\n  ..." if len(lines) > 50 else "")

@tool("grep_files", "Search file contents with regex", {"type": "object", "properties": {
    "pattern": {"type": "string", "description": "Regex pattern to search"},
    "glob": {"type": "string", "description": "File glob filter (e.g. *.py, **/*.md)", "default": "*"},
}, "required": ["pattern"]})
def grep_files(pattern: str, glob: str = "*") -> str:
    results = []
    for p in Path(".").rglob(glob):
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.split("\n"), 1):
                    if __import__("re").search(pattern, line):
                        results.append(f"{p}:{i}: {line.strip()[:120]}")
            except:
                pass
    return "\n".join(results[:100]) + ("\n..." if len(results) > 100 else "") if results else "No matches found"
