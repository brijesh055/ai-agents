"""Brijesh'AI — Textual-based TUI (Claude Code style)"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static, Label
from textual.containers import Container, Horizontal
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

class BrijeshAI(App):
    TITLE = BRAND
    CSS = """
    Screen { background: #0c0c0c; }
    #header {
        height: 1; background: #0c0c0c; padding: 0 1;
        layout: horizontal;
    }
    #brand {
        width: auto; content-align: left middle;
        color: #cccccc; text-style: bold;
    }
    #head-right {
        width: 1fr; content-align: right middle;
        color: #555555;
    }
    #output {
        height: 1fr; border: none; background: #0c0c0c;
        color: #d4d4d4; margin: 0 1; padding: 0 1;
    }
    RichLog { scrollbar-color: #333333 #0c0c0c; scrollbar-size-vertical: 1; }
    #input-row {
        height: 1; margin: 0 1; dock: bottom;
        layout: horizontal;
    }
    #prompt {
        width: 2; content-align: left middle;
        color: #888888; text-style: bold;
    }
    #input {
        height: 1; background: #0c0c0c;
        color: #d4d4d4; border: none; padding: 0;
    }
    #status {
        height: 1; background: #0c0c0c;
        color: #555555; dock: bottom;
        border-top: solid #1a1a1a;
    }
    """

    current_agent = reactive("researcher")
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+l", "clear_screen", "Clear", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Label("Brijesh'AI", id="brand")
            yield Label("", id="head-right")
        yield RichLog(id="output", highlight=True, markup=True, wrap=True, max_lines=3000)
        with Horizontal(id="input-row"):
            yield Label(">", id="prompt")
            yield Input(id="input", placeholder="")
        yield Static(id="status")

    def on_mount(self) -> None:
        self.query_one("#input", Input).focus()
        self._load_session()
        self._discover_skills()
        self._load_plugins()
        self._banner()
        self._update_status()
        self.cost_tracker = CostTracker()

    def _load_plugins(self):
        from core.plugin_manager import discover_plugins, get_registry
        loaded = discover_plugins()
        if loaded:
            out = self.query_one("#output", RichLog)
            out.write(f"[dim #555555]plugins: {', '.join(loaded)}[/dim #555555]")
        self.plugin_registry = get_registry()

    def _banner(self):
        out = self.query_one("#output", RichLog)
        out.write(f"[bold #cccccc]Brijesh'AI[/bold #cccccc] [dim #555555]v2.0 | {self.provider}/{self.model}[/dim #555555]")
        out.write(f"[dim #333333]/help for commands[/dim #333333]")
        out.write("")

    def _discover_skills(self):
        from glob import glob
        self.skills = []
        seen = set()
        for d in [os.path.expanduser("~/.config/opencode/skills"),
                  os.path.expanduser("~/.agents/skills")]:
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
        parts = [f"{self.provider}/{self.model}"]
        if branch:
            parts.append(branch)
        c = getattr(self, 'cost_tracker', None)
        if c:
            s = c.summary()
            parts.append(f"${s['session_cost']:.4f}")
        self.query_one("#status", Static).update("  " + "  |  ".join(parts))

    # --- action_help goes right in output, no separators ---
    def action_help(self):
        out = self.query_one("#output", RichLog)
        out.write("")
        out.write(f"[bold #d4d4d4]Commands[/bold #d4d4d4]")
        out.write(f"[dim #555555]/research[/dim #555555] [dim #555555]<topic>[/dim #555555]")
        out.write(f"[dim #555555]/plan[/dim #555555] [dim #555555]<desc>[/dim #555555]  research 11 sectors + report")
        out.write(f"[dim #555555]/tool[/dim #555555] [dim #555555]<task>[/dim #555555]  tool-using agent")
        out.write(f"[dim #555555]/review[/dim #555555] [dim #555555]<file>[/dim #555555]")
        out.write(f"[dim #555555]/code[/dim #555555] [dim #555555]<file> <instr>[/dim #555555]")
        out.write(f"[dim #555555]/generate[/dim #555555] [dim #555555]<spec>[/dim #555555]")
        out.write(f"[dim #555555]/agent[/dim #555555] [dim #555555]<name>[/dim #555555]")
        out.write(f"[dim #555555]/git[/dim #555555] [dim #555555]status|log|commit|branch|switch|diff[/dim #555555]")
        out.write(f"[dim #555555]/project[/dim #555555]")
        out.write(f"[dim #555555]/plugins[/dim #555555]")
        out.write(f"[dim #555555]/skills[/dim #555555]")
        out.write(f"[dim #555555]/status[/dim #555555]")
        out.write(f"[dim #555555]/clear[/dim #555555]  [dim #555555]/exit[/dim #555555]")

    def action_research(self, topic: str):
        out = self.query_one("#output", RichLog)
        from agents.researcher.agent import ResearcherAgent
        from agents.researcher.prompts import SECTORS_ORDER
        out.write(f"")
        a = ResearcherAgent()
        r = a.research(topic)
        if r.get("type") == "general":
            answer = r.get("answer", "")
            if answer:
                for line in answer.split("\n"):
                    out.write(f"  {line[:200]}")
            return
        sectors = r.get("sectors", {})
        for sector in SECTORS_ORDER:
            text = sectors.get(sector, "")
            if not text or text.startswith("Error"):
                out.write(f"  [dim #555555]{sector}[/dim #555555] [bold #ff6b6b]\u2718[/bold #ff6b6b]")
                continue
            out.write(f"  [dim #555555]{sector}[/dim #555555] [bold #98c379]\u2713[/bold #98c379]")
            first = text.strip().split("\n")[0][:120]
            out.write(f"    [dim #555555]{first}[/dim #555555]")

    @work(thread=True)
    def action_plan(self, description: str):
        from agents.orchestrator.agent import OrchestratorAgent
        out = self.query_one("#output", RichLog)
        out.write(f"")
        out.write(f"[bold #d4d4d4]plan:[/bold #d4d4d4] {description}")
        o = OrchestratorAgent()
        result = o.run_pipeline(description)
        for s in result.get("stages", []):
            name = s["name"]
            status = s["status"]
            output = s.get("output", "")
            icon = "\u2713" if status == "done" else "\u2718"
            cl = "#98c379" if status == "done" else "#ff6b6b"
            out.write(f"  [{cl}]{icon}[/{cl}] [dim #555555]{name}  {output}[/dim #555555]")
        if result.get("type") == "general":
            answer = result.get("results", {}).get("research", {}).get("answer", "")
            if answer:
                for line in answer.split("\n"):
                    out.write(f"  {line[:200]}")
            return
        if result.get("all_passed"):
            report = result.get("results", {}).get("report", "")
            out.write(f"  [dim #555555]\u2500[/dim #555555]" * 50)
            out.write(f"  [bold #d4d4d4]report[/bold #d4d4d4]  [dim #555555]order code \u2192 /code or /generate[/dim #555555]")
            if report:
                for line in report.split("\n"):
                    out.write(f"  {line[:200]}")
        else:
            out.write(f"  [bold #ff6b6b]\u2718 {result.get('failed_at')}[/bold #ff6b6b]")

    @work(thread=True)
    def action_tool(self, task: str):
        from core.tool_runner import ToolRunner
        out = self.query_one("#output", RichLog)
        out.write(f"")
        out.write(f"[bold #d4d4d4]tool:[/bold #d4d4d4] {task}")
        runner = ToolRunner()
        result = runner.run(
            "You are an AI assistant with tool access. Use tools to accomplish the task.",
            task, agent="tool_user",
        )
        for line in result.split("\n")[:30]:
            out.write(f"  {line[:200]}")

    def action_review(self, filepath: str):
        out = self.query_one("#output", RichLog)
        from agents.reviewer.agent import ReviewerAgent
        out.write(f"")
        out.write(f"[bold #d4d4d4]review:[/bold #d4d4d4] {filepath}")
        if not os.path.exists(filepath):
            out.write(f"  [bold #ff6b6b]not found: {filepath}[/bold #ff6b6b]")
            return
        r = ReviewerAgent().review(filepath)
        for i in r.get("issues", []):
            sev = i.get("severity", "error")
            ln = i.get("line", "?")
            cl = "#ff6b6b" if sev == "error" else "#e5c07b" if sev == "warn" else "#555555"
            out.write(f"  [{cl}][{sev}][L{ln}] {i.get('message', '')}[/{cl}]")
        s = r.get("summary", "")
        if s:
            out.write(f"  [dim #555555]{s[:200]}[/dim #555555]")

    def action_code(self, filepath: str, instructions: str):
        out = self.query_one("#output", RichLog)
        from agents.coder.agent import CodingAgent
        out.write(f"")
        out.write(f"[bold #d4d4d4]code:[/bold #d4d4d4] {filepath}")
        r = CodingAgent().modify(filepath, instructions)
        if r.get("success"):
            out.write(f"  [bold #98c379]\u2713 modified[/bold #98c379]")
        else:
            out.write(f"  [bold #ff6b6b]\u2718 {r.get('error', 'Failed')}[/bold #ff6b6b]")

    def action_generate(self, spec: str):
        out = self.query_one("#output", RichLog)
        from agents.coder.agent import CodingAgent
        lang = "python"
        if " --lang " in spec:
            parts = spec.split(" --lang ", 1)
            spec, lang = parts[0], parts[1].strip() or "python"
        out.write(f"")
        out.write(f"[bold #d4d4d4]generate:[/bold #d4d4d4] {lang}")
        r = CodingAgent().generate(spec, lang)
        if r.get("success"):
            code = r["code"]
            out.write(f"  [bold #98c379]\u2713 generated[/bold #98c379]")
            for line in code.split("\n")[:20]:
                out.write(f"  {line}")
        else:
            out.write(f"  [bold #ff6b6b]\u2718 {r.get('error', 'Failed')}[/bold #ff6b6b]")

    def action_status(self):
        out = self.query_one("#output", RichLog)
        s = self.cost_tracker.summary()
        out.write(f"")
        out.write(f"[bold #d4d4d4]status[/bold #d4d4d4]")
        out.write(f"  calls: {s['calls']}")
        out.write(f"  tokens: {s['tokens']['total']} (in: {s['tokens']['input']} out: {s['tokens']['output']})")
        out.write(f"  cost: [bold #e5c07b]${s['session_cost']}[/bold #e5c07b]")
        out.write(f"  [dim #555555]model: {self.provider}/{self.model}[/dim #555555]")

    def action_git(self, sub: str):
        out = self.query_one("#output", RichLog)
        import core.git_tools as git
        out.write(f"")
        out.write(f"[bold #d4d4d4]git:[/bold #d4d4d4] {sub if sub else 'status'}")
        if not git.is_repo():
            out.write(f"  [bold #ff6b6b]not a git repo[/bold #ff6b6b]")
            return
        if sub == "status" or not sub:
            for line in git.status().split("\n"):
                out.write(f"  [dim #555555]{line}[/dim #555555]")
        elif sub == "log":
            for line in git.log(10).split("\n"):
                out.write(f"  [dim #555555]{line}[/dim #555555]")
        elif sub == "branch":
            for b in git.branches():
                out.write(f"  [dim #555555]{b}[/dim #555555]")
        elif sub.startswith("commit"):
            msg = sub.split(" ", 1)[1] if " " in sub else ""
            if not msg:
                msg = git.auto_commit_message()
                out.write(f"  [dim #555555]auto: {msg}[/dim #555555]")
            r = git.commit(msg)
            cl = "#98c379" if r["success"] else "#ff6b6b"
            out.write(f"  [{cl}]{r['output']}[/{cl}]")
        elif sub.startswith("switch") or sub.startswith("checkout"):
            bname = sub.split(" ", 1)[1] if " " in sub else ""
            if not bname:
                out.write("  [dim #555555]usage: /git switch <branch>[/dim #555555]")
                return
            r = git.switch(bname)
            cl = "#98c379" if r["success"] else "#ff6b6b"
            out.write(f"  [{cl}]{r['output']}[/{cl}]")
        elif sub == "diff":
            for line in git.diff().split("\n"):
                out.write(f"  [dim #555555]{line}[/dim #555555]")
        else:
            out.write(f"  [dim #555555]sub: status|log|branch|commit|switch|diff[/dim #555555]")

    def action_project(self):
        out = self.query_one("#output", RichLog)
        from core.project_awareness import summary_text
        out.write(f"")
        out.write(f"[bold #d4d4d4]project[/bold #d4d4d4]")
        for line in summary_text().split("\n"):
            out.write(f"  [dim #555555]{line}[/dim #555555]")

    def action_plugins(self):
        out = self.query_one("#output", RichLog)
        cmds = self.plugin_registry.commands
        agents = self.plugin_registry.agents
        out.write(f"")
        out.write(f"[bold #d4d4d4]plugins[/bold #d4d4d4]")
        if not cmds and not agents:
            out.write("  [dim #555555]none loaded[/dim #555555]")
            return
        for name, info in cmds.items():
            out.write(f"  [dim #555555]/{name}[/dim #555555]  {info['description']}")
        for name, info in agents.items():
            out.write(f"  [dim #555555]{name}[/dim #555555] agent  {info['description']}")

    def action_skills(self):
        out = self.query_one("#output", RichLog)
        out.write(f"")
        out.write(f"[bold #d4d4d4]skills ({len(self.skills)})[/bold #d4d4d4]")
        if not self.skills:
            out.write("  [dim #555555]none[/dim #555555]")
            return
        for name in self.skills:
            out.write(f"  [dim #555555]/{name}[/dim #555555]")

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
            out.write(f"  [bold #ff6b6b]unknown skill: {name}[/bold #ff6b6b]")
            return
        content = open(found, encoding="utf-8").read()[:2000]
        client = LLMClient()
        sys_prompt = f"CRITICAL: Produce the EXACT requested output directly — no disclaimers, no explanations.\n\n{content}"
        user_msg = extra or f"Apply the {name} skill and produce the output."
        r = client.chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ], agent="skill")
        out.write(f"")
        out.write(f"[bold #d4d4d4]skill:[/bold #d4d4d4] {name}")
        for line in r.split("\n")[:40]:
            out.write(f"  {line[:200]}")

    def action_clear(self):
        self.query_one("#output", RichLog).clear()
        self._banner()

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
                if not args: return
                self.action_research(args)
            elif cmd == "plan":
                if not args: return
                self.action_plan(args)
            elif cmd == "tool":
                if not args: return
                self.action_tool(args)
            elif cmd == "review":
                if not args: return
                self.action_review(args)
            elif cmd == "code":
                ps = args.split(" ", 1)
                if len(ps) < 2: return
                self.action_code(ps[0], ps[1])
            elif cmd == "generate":
                if not args: return
                self.action_generate(args)
            elif cmd == "agent":
                if args and args.lower() in AGENTS:
                    self.current_agent = args.lower()
                    self._update_status()
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
                    result = plugin_result["handler"](args)
                    for line in result.split("\n"):
                        self.query_one("#output", RichLog).write(f"  {line}")
                else:
                    self.query_one("#output", RichLog).write(f"  [dim #555555]unknown: /{cmd}[/dim #555555]")
        else:
            sk = self._find_skill(inp.split(" ")[0])
            if sk:
                parts = inp.strip().split(" ", 1)
                self.action_skill(sk, parts[1].strip() if len(parts) > 1 else "")
            else:
                self.action_research(inp)
        self._save_session()

    def _find_skill(self, name: str):
        for s in self.skills:
            if s.lower() == name.lower():
                return s
        return None

    def watch_current_agent(self, value):
        self._update_status()

    def action_clear_screen(self):
        self.action_clear()

    def on_unmount(self):
        self._save_session()

def main():
    BrijeshAI().run()

if __name__ == "__main__":
    main()
