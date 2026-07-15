# Brijesh'AI — Session Memory

## Project
`D:\ai-agents` — local-first multi-agent TUI branded "Brijesh'AI"

## What We Built
- `tui.py` — Interactive TUI with `/` commands, auto-complete, colored output
  - Agents: researcher, coder, reviewer, tester
  - Commands: research, review, code, generate, test, agent, agents, skills, skill, status, help, clear, exit, quit
  - SlashCompleter: dropdown on typing `/`; Tab also triggers completion
  - Toolbar shows current agent + provider/model
  - Skills auto-discovered from ~/.config/opencode/skills/ (49 skills)
  - Session persistence via `.session.json` (resumes agent on restart)
- `ai.bat` / `ai.ps1` — launchers; `ai.bat` copied to Python Scripts dir for global `ai` command
- `core/llm_client.py` — OpenRouter integration working (gpt-3.5-turbo)

## Key Changes Made
1. `&` HTML bug: `Costs & stats` → `Costs and stats` (line 263)
2. HTML tag crash in usage msgs: changed from `p()` to `print()` for usage lines
3. Skill execution: `do_skill()` feeds SKILL.md content as system prompt to LLM
4. Non-command input checks skill name match before doing generic research
5. Session save/restore via `.session.json` (agent, timestamp)
6. `p()` function no longer passes `style=style` (caused HTML parse conflicts)

## User's Understanding
- User types `ai` to launch the TUI
- Types `/skill <name>` or just `<skillname>` to run a skill
- Types any text (no `/`) to research a topic (or run skill if name matches)
- `/exit` or Ctrl+C/D to quit (state auto-saves)

## What User Wants Next
- Skills should produce EXACT output (code, design tokens, etc.) not descriptions
- Prompts updated: "produce output directly — no disclaimers"
- Session persistence so chat context carries across days (solved via this file + .session.json)
- Mobile APK: Convert this project into a mobile app (Android APK). User prefers web app wrapper approach (option 2 - Flask/FastAPI backend + WebView APK). Discuss when they return.

## Config
- Provider: openai (OpenRouter)
- Model: gpt-3.5-turbo
- API key via .env
