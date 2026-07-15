"""Brijesh'AI — Textual-based Rich TUI"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, Label
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from core.llm_client import _load_env, LLMClient
from core.cost_tracker import CostTracker

_load_env()

BRAND = "Brijesh'AI"
AGENTS = {
    "researcher": {"label": "Researcher", "emoji": "\U0001F50D"},
    "coder":      {"label": "Coder",      "emoji": "\U0001F4BB"},
    "reviewer":   {"label": "Reviewer",   "emoji": "\U0001F50D"},
    "tester":     {"label": "Tester",     "emoji": "\u2699\uFE0F"},
}

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session.json")

SEPARATOR = "[dim #2a2a4a]\u2500[/dim #2a2a4a]" * 58

class BrijeshAI(App):
    TITLE = BRAND
    CSS = """
    Screen {
        background: #0a0a1a;
    }
    #header {
        height: 3;
        background: #0d0d24;
        border-bottom: solid #2a2a4a;
        padding: 0 2;
        layout: horizontal;
    }
    #brand-label {
        width: 22;
        content-align: left middle;
        color: #00e5bf;
        text-style: bold;
        padding: 0 1;
    }
    #header-center {
        width: 1fr;
        content-align: center middle;
        color: #6b6b8a;
        text-style: italic;
    }
    #header-right {
        width: 40;
        content-align: right middle;
        color: #6b6b8a;
    }
    #output {
        height: 1fr;
        border: none;
        background: #0a0a1a;
        color: #e8e8f0;
        margin: 0 1;
        padding: 0 1;
    }
    RichLog {
        scrollbar-color: #2a2a4a #0d0d24;
        scrollbar-size-vertical: 1;
    }
    #input-container {
        height: 3;
        margin: 0 1 0 1;
        dock: bottom;
        background: #0d0d24;
        border: solid #2a2a4a;
    }
    #input-prefix {
        width: 3;
        content-align: center middle;
        color: #00e5bf;
        text-style: bold;
        background: #0d0d24;
    }
    #input {
        background: #0d0d24;
        color: #e8e8f0;
        border: none;
        padding: 0 1;
    }
    #input:focus {
        background: #0d0d24;
    }
    #status-bar {
        height: 1;
        background: #0d0d24;
        color: #6b6b8a;
        text-align: center;
        border-top: solid #1a1a3a;
    }
    .cmd-header {
        color: #00e5bf;
        text-style: bold;
    }
    .cmd-accent {
        color: #ffb347;
        text-style: bold;
    }
    .cmd-success {
        color: #00e5bf;
    }
    .cmd-error {
        color: #ff5252;
        text-style: bold;
    }
    .cmd-dim {
        color: #6b6b8a;
        text-style: italic;
    }
    .cmd-prompt {
        color: #00e5bf;
        text-style: bold;
    }
    """

    current_agent = reactive("researcher")
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+l", "clear_screen", "Clear", show=False),
        Binding("ctrl+p", "focus_input", "Input", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Label(f"[bold #00e5bf]Brijesh'AI[/bold #00e5bf] [dim #6b6b8a]v2.0[/dim #6b6b8a]", id="brand-label")
            yield Label("multi-agent engineering platform", id="header-center")
            yield Label("", id="header-right")
        yield RichLog(id="output", highlight=True, markup=True, wrap=True, max_lines=3000)
        with Horizontal(id="input-container"):
            yield Label("\xbb", id="input-prefix")
            yield Input(id="input", placeholder="Type /help for commands, or just ask a question...")
        yield Static(id="status-bar")

    def on_mount(self) -> None:
        self.query_one("#input", Input).focus()
        self._load_session()
        self._discover_skills()
        self._load_plugins()
        self._banner()
        self._update_status()
        from core.cost_tracker import CostTracker
        self.cost_tracker = CostTracker()

    def _load_plugins(self):
        from core.plugin_manager import discover_plugins, get_registry
        loaded = discover_plugins()
        if loaded:
            out = self.query_one("#output", RichLog)
            out.write(f"  [dim #6b6b8a]\u25B8 plugins loaded: {', '.join(loaded)}[/dim #6b6b8a]")
        self.plugin_registry = get_registry()

    def _banner(self):
        out = self.query_one("#output", RichLog)
        out.write("")
        out.write(f"  [bold #00e5bf]  .--.      .--.   [/bold #00e5bf]")
        out.write(f"  [bold #00e5bf]  |   \\    /   |   [/bold #00e5bf]")
        out.write(f"  [bold #00e5bf]  |    \\  /    |   [/bold #00e5bf]  [bold #e8e8f0]Brijesh'AI[/bold #e8e8f0]  [dim #6b6b8a]v2.0[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]  |     \\/     |   [/bold #00e5bf]  [dim #6b6b8a]multi-agent engineering platform[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]  |            |   [/bold #00e5bf]")
        out.write(f"  [bold #00e5bf]  '------------'   [/bold #00e5bf]")
        agent = AGENTS[self.current_agent]
        out.write(f"  [dim #6b6b8a]agent: {agent['label']}  |  {self.provider}/{self.model}[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")
        out.write("")

    def _discover_skills(self):
        from glob import glob
        self.skills = []
        seen = set()
        search_dirs = [
            os.path.expanduser("~/.config/opencode/skills"),
            os.path.expanduser("~/.agents/skills"),
        ]
        for d in search_dirs:
            for f in glob(os.path.join(d, "**/SKILL.md"), recursive=True):
                name = Path(f).parent.name
                if name not in seen:
                    seen.add(name)
                    self.skills.append(name)
        self.skills.sort()

    def _save_session(self):
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump({"current_agent": self.current_agent,
                    "timestamp": __import__("datetime").datetime.now().isoformat()}, f)
        except:
            pass

    def _load_session(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE) as f:
                    data = json.load(f)
                self.current_agent = data.get("current_agent", self.current_agent)
            except:
                pass

    def _update_status(self):
        agent = AGENTS[self.current_agent]
        try:
            import core.git_tools as git
            branch = git.branch() if git.is_repo() else ""
        except:
            branch = ""
        parts = [f"{agent['emoji']} {agent['label']}  |  {self.provider}/{self.model}"]
        if branch:
            parts.append(f"  \u2387 {branch}")
        cost = getattr(self, 'cost_tracker', None)
        if cost:
            s = cost.summary()
            parts.append(f"  ${s['session_cost']:.4f}")
        bar = self.query_one("#status-bar", Static)
        bar.update("  " + "  |".join(parts) + f"  |  {BRAND}")

    def _write_header(self, label: str, topic: str):
        out = self.query_one("#output", RichLog)
        out.write(f"  {SEPARATOR}")
        out.write(f"  [bold #00e5bf]\u25B6[/bold #00e5bf]  [bold #ffb347]{label}[/bold #ffb347]  [dim #6b6b8a]{topic}[/dim #6b6b8a]")

    def action_research(self, topic: str):
        out = self.query_one("#output", RichLog)
        from agents.researcher.agent import ResearcherAgent
        from agents.researcher.prompts import SECTORS_ORDER
        self._write_header("RESEARCH", topic)
        a = ResearcherAgent()
        r = a.research(topic)
        if r.get("type") == "general":
            answer = r.get("answer", "")
            if answer:
                for line in answer.split("\n"):
                    out.write(f"  {line[:200]}")
            out.write(f"  {SEPARATOR}")
            return
        sectors = r.get("sectors", {})
        for sector in SECTORS_ORDER:
            text = sectors.get(sector, "")
            if not text or text.startswith("Error"):
                out.write(f"  [bold #ff5252]\u2718 {sector.upper()}: error[/bold #ff5252]")
                continue
            out.write(f"")
            out.write(f"  [bold #ffb347]\u25B6 {sector.upper()}[/bold #ffb347]")
            for line in text.strip().split("\n")[:5]:
                out.write(f"    {line[:160]}")
        out.write(f"  {SEPARATOR}")

    @work(thread=True)
    def action_plan(self, description: str):
        from agents.orchestrator.agent import OrchestratorAgent
        out = self.query_one("#output", RichLog)
        self._write_header("PLAN", description)
        o = OrchestratorAgent()
        result = o.run_pipeline(description)
        for s in result.get("stages", []):
            name = s["name"]
            status = s["status"]
            output = s.get("output", "")
            icon = "\u2713" if status == "done" else "\u2718"
            cl = "#00e5bf" if status == "done" else "#ff5252"
            out.write(f"  [{cl}]{icon} {name.upper()}[/{cl}]  [dim #6b6b8a]{output}[/dim #6b6b8a]")
        if result.get("type") == "general":
            answer = result.get("results", {}).get("research", {}).get("answer", "")
            if answer:
                out.write("")
                for line in answer.split("\n"):
                    out.write(f"  {line[:200]}")
            out.write(f"  {SEPARATOR}")
            return
        if result.get("all_passed"):
            report = result.get("results", {}).get("report", "")
            out.write(f"")
            out.write(f"  [bold #00e5bf]\u2500[/bold #00e5bf]" * 58)
            out.write(f"  [bold #ffb347]FINAL REPORT[/bold #ffb347]")
            out.write(f"  [dim #6b6b8a]Review below \u2192 then order code: /code <file> <instr> | /generate <spec>[/dim #6b6b8a]")
            out.write("")
            if report:
                for line in report.split("\n"):
                    out.write(f"  {line[:200]}")
        else:
            out.write(f"  [bold #ff5252]\u2718 Plan failed at: {result.get('failed_at')}[/bold #ff5252]")
        out.write(f"  {SEPARATOR}")

    @work(thread=True)
    def action_tool(self, task: str):
        from core.tool_runner import ToolRunner
        out = self.query_one("#output", RichLog)
        self._write_header("TOOL", task)
        runner = ToolRunner()
        result = runner.run(
            "You are an AI assistant with tool access. Use tools to accomplish the task.",
            task, agent="tool_user",
        )
        for line in result.split("\n")[:30]:
            out.write(f"  {line[:160]}")
        out.write(f"  {SEPARATOR}")

    def action_review(self, filepath: str):
        out = self.query_one("#output", RichLog)
        from agents.reviewer.agent import ReviewerAgent
        self._write_header("REVIEW", filepath)
        if not os.path.exists(filepath):
            out.write(f"  [bold #ff5252]File not found: {filepath}[/bold #ff5252]")
            out.write(f"  {SEPARATOR}")
            return
        r = ReviewerAgent().review(filepath)
        for i in r.get("issues", []):
            sev = i.get("severity", "info")
            ln = i.get("line", "?")
            cl = {"error": "#ff5252", "warn": "#ffb347", "info": "#6b6b8a"}.get(sev, "#6b6b8a")
            out.write(f"  [{cl}][{sev.upper()}][L{ln}] {i.get('message', '')}[/{cl}]")
        s = r.get("summary", "")
        if s:
            out.write(f"  [dim #6b6b8a]{s[:200]}[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")

    def action_code(self, filepath: str, instructions: str):
        out = self.query_one("#output", RichLog)
        from agents.coder.agent import CodingAgent
        self._write_header("CODE", f"{filepath}")
        r = CodingAgent().modify(filepath, instructions)
        if r.get("success"):
            out.write(f"  [bold #00e5bf]\u2713 Modified {filepath}[/bold #00e5bf]")
        else:
            out.write(f"  [bold #ff5252]\u2718 {r.get('error', 'Failed')}[/bold #ff5252]")
        out.write(f"  {SEPARATOR}")

    def action_generate(self, spec: str):
        out = self.query_one("#output", RichLog)
        from agents.coder.agent import CodingAgent
        lang = "python"
        if " --lang " in spec:
            parts = spec.split(" --lang ", 1)
            spec, lang = parts[0], parts[1].strip() or "python"
        self._write_header("GENERATE", f"{lang}")
        r = CodingAgent().generate(spec, lang)
        if r.get("success"):
            code = r["code"]
            out.write(f"  [bold #00e5bf]\u2713 Generated {lang} code:[/bold #00e5bf]")
            for line in code.split("\n")[:20]:
                out.write(f"    {line}")
        else:
            out.write(f"  [bold #ff5252]\u2718 {r.get('error', 'Failed')}[/bold #ff5252]")
        out.write(f"  {SEPARATOR}")

    def action_status(self):
        out = self.query_one("#output", RichLog)
        s = self.cost_tracker.summary()
        out.write(f"")
        out.write(f"  [bold #ffb347]Session Status[/bold #ffb347]")
        out.write(f"  [bold #00e5bf]\u2500[/bold #00e5bf]" * 40)
        out.write(f"    calls : {s['calls']}")
        out.write(f"    tokens: {s['tokens']['total']}  (in: {s['tokens']['input']}  out: {s['tokens']['output']})")
        out.write(f"    cost  : [bold #ffb347]${s['session_cost']}[/bold #ffb347]")
        out.write(f"    [dim #6b6b8a]model: {self.provider}/{self.model}[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")

    def action_git(self, sub: str):
        out = self.query_one("#output", RichLog)
        import core.git_tools as git
        self._write_header("GIT", sub if sub else "status")
        if not git.is_repo():
            out.write(f"  [bold #ff5252]Not a git repository[/bold #ff5252]")
            out.write(f"  {SEPARATOR}")
            return
        if sub == "status" or not sub:
            out.write(f"  [dim #6b6b8a]" + git.status().replace("\n", "\n  ") + "[/dim #6b6b8a]")
        elif sub == "log":
            out.write(f"  [dim #6b6b8a]" + git.log(10).replace("\n", "\n  ") + "[/dim #6b6b8a]")
        elif sub == "branch":
            out.write(f"  [dim #6b6b8a]" + "\n  ".join(git.branches()) + "[/dim #6b6b8a]")
        elif sub.startswith("commit"):
            msg = sub.split(" ", 1)[1] if " " in sub else ""
            if not msg:
                msg = git.auto_commit_message()
                out.write(f"  [dim #6b6b8a]auto: {msg}[/dim #6b6b8a]")
            r = git.commit(msg)
            if r["success"]:
                out.write(f"  [bold #00e5bf]\u2713 {r['output']}[/bold #00e5bf]")
            else:
                out.write(f"  [bold #ff5252]\u2718 {r['output']}[/bold #ff5252]")
        elif sub.startswith("switch") or sub.startswith("checkout"):
            branch_name = sub.split(" ", 1)[1] if " " in sub else ""
            if not branch_name:
                out.write("  Usage: /git switch <branch>")
                out.write(f"  {SEPARATOR}")
                return
            r = git.switch(branch_name)
            if r["success"]:
                out.write(f"  [bold #00e5bf]\u2713 Switched to {branch_name}[/bold #00e5bf]")
            else:
                out.write(f"  [bold #ff5252]\u2718 {r['output']}[/bold #ff5252]")
        elif sub == "diff":
            out.write(f"  [dim #6b6b8a]" + git.diff().replace("\n", "\n  ") + "[/dim #6b6b8a]")
        else:
            out.write(f"  [dim #6b6b8a]subcommands: status, log, branch, commit <msg>, switch <b>, diff[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")

    def action_project(self):
        out = self.query_one("#output", RichLog)
        from core.project_awareness import summary_text
        self._write_header("PROJECT", "")
        out.write(f"  [dim #6b6b8a]" + summary_text().replace("\n", "\n  ") + "[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")

    def action_plugins(self):
        out = self.query_one("#output", RichLog)
        cmds = self.plugin_registry.commands
        agents = self.plugin_registry.agents
        self._write_header("PLUGINS", "")
        if not cmds and not agents:
            out.write("  [dim #6b6b8a]No plugins loaded.[/dim #6b6b8a]")
            out.write(f"  {SEPARATOR}")
            return
        for name, info in cmds.items():
            out.write(f"  [bold #ffb347]/{name}[/bold #ffb347]  [dim #6b6b8a]{info['description']}[/dim #6b6b8a]")
        for name, info in agents.items():
            out.write(f"  [bold #ffb347]{name}[/bold #ffb347] agent  [dim #6b6b8a]{info['description']}[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")

    def action_skills(self):
        out = self.query_one("#output", RichLog)
        self._write_header("SKILLS", f"{len(self.skills)} available")
        if not self.skills:
            out.write("  [dim #6b6b8a]No skills discovered.[/dim #6b6b8a]")
            out.write(f"  {SEPARATOR}")
            return
        for name in self.skills:
            out.write(f"  [bold #ffb347]/[/bold #ffb347][bold #00e5bf]{name}[/bold #00e5bf]")
        out.write(f"  {SEPARATOR}")

    def action_skill(self, name: str, extra: str = ""):
        out = self.query_one("#output", RichLog)
        from glob import glob
        found = None
        for d in [os.path.expanduser("~/.config/opencode/skills"),
                  os.path.expanduser("~/.agents/skills")]:
            for f in glob(os.path.join(d, "**/SKILL.md"), recursive=True):
                if Path(f).parent.name.lower() == name.lower():
                    found = f
                    break
        if not found:
            out.write(f"  [bold #ff5252]Unknown skill: {name}[/bold #ff5252]")
            out.write(f"  {SEPARATOR}")
            return
        content = open(found, encoding="utf-8").read()[:2000]
        client = LLMClient()
        sys_prompt = f"CRITICAL: Produce the EXACT requested output directly — no disclaimers, no explanations.\n\n{content}"
        user_msg = extra or f"Apply the {name} skill and produce the output."
        r = client.chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ], agent="skill")
        self._write_header("SKILL", name)
        for line in r.split("\n")[:40]:
            out.write(f"  {line[:160]}")
        out.write(f"  {SEPARATOR}")

    def action_clear(self):
        self.query_one("#output", RichLog).clear()
        self._banner()

    def action_help(self):
        out = self.query_one("#output", RichLog)
        out.write(f"")
        out.write(f"  [bold #ffb347]Commands[/bold #ffb347]")
        out.write(f"  [bold #00e5bf]\u2500[/bold #00e5bf]" * 40)
        out.write(f"  [bold #00e5bf]/research[/bold #00e5bf]  [dim #6b6b8a]<topic>[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/plan[/bold #00e5bf]      [dim #6b6b8a]<desc>[/dim #6b6b8a]     research 11 sectors + final report")
        out.write(f"  [bold #00e5bf]/tool[/bold #00e5bf]       [dim #6b6b8a]<task>[/dim #6b6b8a]     agent with file/shell/web tools")
        out.write(f"  [bold #00e5bf]/review[/bold #00e5bf]     [dim #6b6b8a]<file>[/dim #6b6b8a]     code review")
        out.write(f"  [bold #00e5bf]/code[/bold #00e5bf]       [dim #6b6b8a]<file> <desc>[/dim #6b6b8a]     modify code")
        out.write(f"  [bold #00e5bf]/generate[/bold #00e5bf]   [dim #6b6b8a]<spec>[/dim #6b6b8a]     generate code")
        out.write(f"  [bold #00e5bf]/agent[/bold #00e5bf]      [dim #6b6b8a]<name>[/dim #6b6b8a]     switch agent")
        out.write(f"  [bold #00e5bf]/git[/bold #00e5bf]        [dim #6b6b8a]status|log|commit|branch|switch|diff[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/project[/bold #00e5bf]    [dim #6b6b8a]project overview[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/plugins[/bold #00e5bf]    [dim #6b6b8a]list plugins[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/skills[/bold #00e5bf]     [dim #6b6b8a]list skills[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/status[/bold #00e5bf]     [dim #6b6b8a]costs and stats[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/clear[/bold #00e5bf]      [dim #6b6b8a]clear screen[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/help[/bold #00e5bf]       [dim #6b6b8a]this help[/dim #6b6b8a]")
        out.write(f"  [bold #00e5bf]/exit[/bold #00e5bf]       [dim #6b6b8a]quit[/dim #6b6b8a]")
        out.write(f"  {SEPARATOR}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        inp = event.value.strip()
        self.query_one("#input", Input).clear()
        if not inp:
            return
        if inp.startswith("/"):
            parts = inp[1:].strip().split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1].strip() if len(parts) > 1 else ""
            if cmd == "research":
                if not args: self._usage("research <topic>"); return
                self.action_research(args)
            elif cmd == "plan":
                if not args: self._usage("plan <desc>"); return
                self.action_plan(args)
            elif cmd == "tool":
                if not args: self._usage("tool <task>"); return
                self.action_tool(args)
            elif cmd == "review":
                if not args: self._usage("review <file>"); return
                self.action_review(args)
            elif cmd == "code":
                ps = args.split(" ", 1)
                if len(ps) < 2: self._usage("code <file> <instr>"); return
                self.action_code(ps[0], ps[1])
            elif cmd == "generate":
                if not args: self._usage("generate <spec>"); return
                self.action_generate(args)
            elif cmd == "agent":
                if args and args.lower() in AGENTS:
                    self.current_agent = args.lower()
                    self._update_status()
                else:
                    out = self.query_one("#output", RichLog)
                    out.write(f"  [dim #6b6b8a]agents: {', '.join(AGENTS.keys())}[/dim #6b6b8a]")
                    out.write(f"  {SEPARATOR}")
            elif cmd == "git":
                self.action_git(args)
            elif cmd == "project":
                self.action_project()
            elif cmd == "plugins":
                self.action_plugins()
            elif cmd == "skills":
                self.action_skills()
            elif cmd == "skill":
                ps = args.split(" ", 1)
                self.action_skill(ps[0], ps[1].strip() if len(ps) > 1 else "")
            elif cmd == "status":
                self.action_status()
            elif cmd == "help":
                self.action_help()
            elif cmd == "clear":
                self.action_clear()
            elif cmd in ("exit", "quit"):
                self._save_session()
                self.exit()
            else:
                plugin_result = self.plugin_registry.commands.get(cmd)
                if plugin_result:
                    out = self.query_one("#output", RichLog)
                    result = plugin_result["handler"](args)
                    for line in result.split("\n"):
                        out.write(f"  {line}")
                else:
                    out = self.query_one("#output", RichLog)
                    out.write(f"  [bold #ff5252]unknown: /{cmd}[/bold #ff5252]  [dim #6b6b8a]/help[/dim #6b6b8a]")
                    out.write(f"  {SEPARATOR}")
        else:
            sk = self._find_skill(inp.split(" ")[0])
            if sk:
                parts = inp.strip().split(" ", 1)
                self.action_skill(sk, parts[1].strip() if len(parts) > 1 else "")
            else:
                self.action_research(inp)
        self._save_session()

    def _usage(self, msg: str):
        out = self.query_one("#output", RichLog)
        out.write(f"  [dim #6b6b8a]usage: /{msg}[/dim #6b6b8a]")

    def _find_skill(self, name: str):
        for s in self.skills:
            if s.lower() == name.lower():
                return s
        return None

    def watch_current_agent(self, value):
        self._update_status()

    def action_focus_input(self):
        self.query_one("#input", Input).focus()

    def action_clear_screen(self):
        self.action_clear()

    def on_unmount(self):
        self._save_session()

def main():
    app = BrijeshAI()
    app.run()

if __name__ == "__main__":
    main()
