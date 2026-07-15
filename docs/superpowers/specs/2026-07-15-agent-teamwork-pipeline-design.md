# Agent Teamwork Pipeline — Design Spec

## Overview
Add a `/plan` command to Brijesh'AI that chains all 4 agents (researcher → coder → reviewer → tester) into a single automated pipeline. Each agent passes context to the next via the existing handoff system.

## Command
```
/plan <description>
```
Example: `/plan build a FastAPI login page with JWT auth`

Auto-runs: Researcher → Coder → Reviewer → Tester in sequence.

## Pipeline Flow

```
User input
    │
    ▼
┌──────────────┐    handoff context    ┌──────────────┐
│  Researcher   │ ──────────────────►  │    Coder     │
│  (5-lens      │    topic analysis    │  (generates   │
│   analysis)   │                      │   code files) │
└──────────────┘                      └───────┬───────┘
                                              │ handoff context
                                              │ (code + file paths)
                                              ▼
┌──────────────┐    handoff context    ┌──────────────┐
│   Tester     │ ◄──────────────────  │   Reviewer   │
│  (web test   │    reviewed code     │  (code review │
│   or unit)   │                      │   + issues)   │
└──────────────┘                      └──────────────┘
    │
    ▼
┌────────────────────────────────────────────┐
│         Pipeline Summary Report            │
│  • Research findings (summary)             │
│  • Files generated                         │
│  • Review issues (count + top items)       │
│  • Test results (pass/fail)               │
└────────────────────────────────────────────┘
```

## New/Modified Files

### `agents/orchestrator/agent.py` (NEW)
- `OrchestratorAgent` class
- `run_pipeline(description: str) -> dict` method
  - Instantiates each agent in sequence
  - Passes handoff context between them via `AgentHandoff.pass_context()`
  - Collects results from each stage
  - Returns full pipeline summary

### `tui.py` (MODIFY)
- Add `"plan"` to `COMMANDS` list
- Add `do_plan(description)` function
- Wire in `run()` dispatch for `plan`
- Show inline progress during pipeline (agent name, status)

### `agents/coder/agent.py` (MODIFY)
- `generate()` method checks handoff context for research data before generating
- Adds research context as additional system context if available

### `agents/reviewer/agent.py` (MODIFY)
- `review()` method checks handoff context for code output if no file path given
- Can review generated code from memory instead of just file paths

### `agents/web_tester/agent.py` (MODIFY)
- Accepts code context from handoff for testing generated endpoints

## Progress Display
During pipeline execution, show:
```
  ════════════════════════════════════════
   🔬 PLAN: build a FastAPI login page
  ════════════════════════════════════════
   [1/4] 🔍 Researcher  analyzing...  DONE
   [2/4] 💻 Coder       generating...  DONE → app.py, auth.py
   [3/4] 🔎 Reviewer    reviewing...   DONE → 2 warnings
   [4/4] ⚙ Tester       testing...     DONE → 3/3 passed
  ════════════════════════════════════════
```

## Error Handling
- If any stage fails, pipeline stops with clear error showing which stage failed
- Partial results preserved in handoff for retry

## Success Criteria
- `/plan build a login page` generates working code
- Context passes correctly from research → code → review → test
- Pipeline stops gracefully on failure
- Progress display is readable and real-time
