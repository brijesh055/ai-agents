# AI Agents

One command, local-first, safety-gated multi-agent workflows — without the bloat.

## Installation

```bash
pip install litellm click pydantic playwright
playwright install chromium
```

## Quick Start

```bash
# Run the demo workflow
python quickstart/default_workflow.py "a Python CLI calculator"
```

## CLI Usage

```bash
# Research a topic
python -m cli.main research --topic "quantum computing"

# Run a bug fix workflow
python -m cli.main run bug_fix --issue "Fix null pointer in main.py"

# Review code
python -m cli.main review main.py

# Start dashboard
python -m cli.main dashboard --port 8080

# View session status
python -m cli.main status
```

## Architecture

```
ai-agents/
├── cli/            # CLI entry point & output formatting
├── core/           # Shared infrastructure (LLM, memory, handoff, cost)
├── agents/         # Specialized agents (researcher, tester, coder, reviewer)
├── workflows/      # Pre-built pipelines (bug fix, feature, PR review, docs)
├── sandbox/        # Safety layer (code execution, file access, approval gates)
├── plugins/        # Plugin system (Slack, Jira, Git)
├── observability/  # Logging, metrics, trace viewer, dashboard
├── quickstart/     # Init wizard & demo scripts
└── tests/          # Test suite
```

## Key Differentiators

| vs AutoGPT | Safety sandbox, approval gates, structured handoff |
| vs CrewAI | CLI-first, pre-built workflows, no glue code needed |
| vs LangChain | 4 core deps, opinionated pipelines, local-first |
