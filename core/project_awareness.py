import os, json
from pathlib import Path
from collections import Counter

ROOT = Path(os.getcwd())

def analyze() -> dict:
    info = {
        "name": ROOT.name,
        "language": _detect_language(),
        "framework": _detect_framework(),
        "file_count": 0,
        "dir_count": 0,
        "key_files": [],
        "dependencies": _detect_dependencies(),
        "structure": _summarize_structure(),
    }
    py_files = list(ROOT.rglob("*.py"))
    info["file_count"] = len(py_files) + len(list(ROOT.rglob("*.js"))) + len(list(ROOT.rglob("*.ts")))
    info["dir_count"] = len([d for d in ROOT.rglob("*") if d.is_dir() and ".git" not in str(d)])
    info["key_files"] = _key_files()
    return info

def _detect_language() -> str:
    exts = Counter()
    for f in ROOT.rglob("*"):
        if f.is_file() and ".git" not in str(f):
            ext = f.suffix.lower()
            if ext in (".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".cs"):
                exts[ext] += 1
    if not exts:
        return "unknown"
    lang_map = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".go": "Go",
                ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
                ".c": "C", ".cpp": "C++", ".cs": "C#"}
    top = exts.most_common(1)[0][0]
    return lang_map.get(top, top)

def _detect_framework() -> str:
    files = {str(f.relative_to(ROOT)) for f in ROOT.rglob("*") if f.is_file()}
    checks = {
        "FastAPI": ["requirements.txt", "pyproject.toml"],
        "Flask": ["requirements.txt", "pyproject.toml"],
        "Django": ["manage.py"],
        "React": ["package.json"],
        "Next.js": ["next.config.js", "next.config.ts"],
        "Node.js": ["package.json"],
        "Express": ["package.json"],
        "Textual": ["requirements.txt", "pyproject.toml"],
    }
    for framework, markers in checks.items():
        for m in markers:
            if m in files:
                return framework
    return "unknown"

def _detect_dependencies() -> dict:
    deps = {}
    req_file = ROOT / "requirements.txt"
    if req_file.exists():
        deps["python"] = [l.strip() for l in req_file.read_text().split("\n") if l.strip() and not l.startswith("#")]
    pkg_file = ROOT / "package.json"
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text())
            deps["node"] = list(pkg.get("dependencies", {}).keys())
            deps["node_dev"] = list(pkg.get("devDependencies", {}).keys())
        except:
            pass
    return deps

def _key_files() -> list:
    important = ["README.md", "CLAUDE.md", "requirements.txt", "package.json", "pyproject.toml",
                 "Dockerfile", "docker-compose.yml", "Makefile", ".env.example", "main.py", "app.py",
                 "tui.py", "tui_app.py", "index.js", "index.ts"]
    found = []
    for name in important:
        f = ROOT / name
        if f.exists():
            found.append({"name": name, "size": f.stat().st_size})
    return found

def _summarize_structure() -> list:
    entries = []
    for item in sorted(ROOT.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            py_count = len(list(item.rglob("*.py")))
            entries.append({"name": item.name + "/", "type": "dir", "files": py_count})
        else:
            entries.append({"name": item.name, "type": "file", "size": item.stat().st_size})
    return entries[:30]

def summary_text() -> str:
    info = analyze()
    lines = [f"Project: {info['name']}", f"Language: {info['language']}", f"Framework: {info['framework']}"]
    lines.append(f"Files: {info['file_count']} in {info['dir_count']} directories")
    if info["key_files"]:
        lines.append(f"Key files: {', '.join(k['name'] for k in info['key_files'])}")
    deps = info.get("dependencies", {})
    if deps.get("python"):
        lines.append(f"Python deps: {len(deps['python'])} packages")
    if deps.get("node"):
        lines.append(f"Node deps: {len(deps['node'])} packages")
    return "\n".join(lines)
