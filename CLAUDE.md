# Brijesh'AI — Session Memory

## Project
`D:\ai-agents` — local-first multi-agent TUI branded "Brijesh'AI"

## What We Built (5 Phases)

### Phase 1 — Agent Teamwork Pipeline
- `/plan <desc>` command — full pipeline: research → code → review → validate
- `agents/orchestrator/agent.py` — OrchestratorAgent chains all 4 agents
- Handoff context flows between stages via `AgentHandoff`
- Stage progress shown inline with status indicators

### Phase 2 — Tool-Using Agents
- `/tool <task>` command — agent with file/shell/web tool access
- `core/tools.py` — 6 tools: read_file, write_file, run_command, list_files, grep_files
- `core/tool_runner.py` — Tool-calling loop (agent requests tools → system executes → agent continues)
- Tool call via JSON: `{"tool": "read_file", "args": {"path": "foo.py"}}`

### Phase 3 — Rich Terminal UI (Textual)
- `tui_app.py` — New Textual-based TUI (replaces old prompt_toolkit version)
- Header with brand, scrollable RichLog output, input bar, status bar
- CSS-like styling with dark theme (blues/teals)
- Threaded execution for long-running commands

### Phase 4 — Git & Project Awareness
- `/git status|log|commit|branch|switch|diff` — full git integration
- `/project` — auto-detect language, framework, deps, key files, structure
- `core/git_tools.py` — Git wrapper (status, diff, log, commit, branches)
- `core/project_awareness.py` — Project analyzer (language, framework, deps)

### Phase 5 — Plugin System
- Drop `.py` files in `plugins/` to add commands & agents
- `/plugins` — list loaded plugins
- `core/plugin_manager.py` — Hot-loads modules, registers commands/agents
- Example: `plugins/hello_world.py` adds `/hello` command + HelloBot agent

### Infrastructure
- `tui.py` — Legacy lightweight TUI (still works, `python tui.py`)
- `tui_app.py` — New Textual TUI (default: `python tui_app.py` or `ai`)
- `ai.bat` / `ai.ps1` — launchers pointing to tui_app.py
- Session persistence via `.session.json`

## Config
- Provider: openai (OpenRouter) via .env
- Model: gpt-3.5-turbo
- API key via .env
- For APK: replace OpenRouter with Ollama (local inference)

## Next Steps
- APK packaging (Flask/FastAPI backend + WebView wrapper)
- Voice commands (planned)
