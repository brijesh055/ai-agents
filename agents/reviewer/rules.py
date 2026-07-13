RULES = {
    "no_print_statements": {
        "description": "Avoid print() in production code, use logging instead.",
        "pattern": r"print\(",
        "severity": "warn",
        "category": "style",
    },
    "no_hardcoded_secrets": {
        "description": "No hardcoded API keys, passwords, tokens, or secrets.",
        "pattern": "(api_key|password|secret|token|auth_token|access_key)\\s*=\\s*['\"]",
        "severity": "error",
        "category": "security",
    },
    "function_docstrings": {
        "description": "Functions should have docstrings describing their purpose.",
        "severity": "warn",
        "category": "style",
    },
    "no_bare_excepts": {
        "description": "Avoid bare 'except:' clauses; catch specific exceptions.",
        "pattern": "except\\s*:",
        "severity": "error",
        "category": "correctness",
    },
    "max_line_length": {
        "description": "Lines should not exceed 120 characters.",
        "severity": "warn",
        "category": "style",
    },
    "no_todo_in_production": {
        "description": "Remove TODO, FIXME, HACK, XXX comments from production code.",
        "pattern": "#\\s*(TODO|FIXME|HACK|XXX)\\b",
        "severity": "warn",
        "category": "maintainability",
    },
    "import_on_separate_lines": {
        "description": "Use one import per line instead of importing multiple symbols on one line.",
        "pattern": "from\\s+\\S+\\s+import\\s+\\S+\\s*,\\s*\\S+",
        "severity": "warn",
        "category": "style",
    },
    "no_eval": {
        "description": "Avoid eval(), exec(), or compile() with untrusted input — security risk.",
        "pattern": "\\b(eval|exec)\\s*\\(",
        "severity": "error",
        "category": "security",
    },
    "no_mutable_defaults": {
        "description": "Do not use mutable objects (list, dict, set) as default arguments.",
        "pattern": (
            r"def\s+\w+\s*\([^)]*=\s*\[\s*\]"
            r"|def\s+\w+\s*\([^)]*=\s*\{\s*\}"
            r"|def\s+\w+\s*\([^)]*=\s*set\s*\(\s*\)"
        ),
        "severity": "error",
        "category": "correctness",
    },
    "no_assert_in_production": {
        "description": "assert statements are stripped when Python is optimized (-O); use proper validation.",
        "pattern": "\\bassert\\s+",
        "severity": "warn",
        "category": "correctness",
    },
    "no_wildcard_imports": {
        "description": "Avoid 'from module import *' — pollutes namespace and hides dependencies.",
        "pattern": "from\\s+\\S+\\s+import\\s+\\*",
        "severity": "warn",
        "category": "style",
    },
    "no_compare_with_none": {
        "description": "Use 'is None' instead of '= is None' for None comparisons.",
        "pattern": "==\\s*None|! is None",
        "severity": "warn",
        "category": "style",
    },
}

CATEGORIES = {
    "security": ["no_hardcoded_secrets", "no_eval"],
    "correctness": ["no_bare_excepts", "no_mutable_defaults", "no_assert_in_production"],
    "style": ["no_print_statements", "function_docstrings", "max_line_length", "import_on_separate_lines",
        "no_wildcard_imports", "no_compare_with_none"],
    "maintainability": ["no_todo_in_production"],
}


def get_rules(categories: list[str] = None) -> list[dict]:
    if categories is None:
        return [{"name": k, **v} for k, v in RULES.items()]
    names = set()
    for cat in categories:
        for name in CATEGORIES.get(cat, []):
            names.add(name)
    return [{"name": name, **RULES[name]} for name in sorted(names) if name in RULES]


def get_rule(name: str) -> dict | None:
    rule = RULES.get(name)
    if rule is None:
        return None
    return {"name": name, **rule}
