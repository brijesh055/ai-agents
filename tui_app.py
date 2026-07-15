"""Brijesh'AI — Textual-based Rich TUI"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual.containers import Container, Horizontal
from textual.screen import Screen
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
    Screen {
        background: #1a1a2e;
    }
    Header {
        background: #16213e;
        color: #00d4aa;
        text-style: bold;
    }
    Footer {
        background: #16213e;
        color: #888888;
    }
    #output {
        height: 1fr;
        border: solid #0f3460;
        background: #1a1a2e;
        color: #e0e0e0;
        margin: 0 1;
    }
    #input-container {
        height: 3;
        margin: 0 1;
        dock: bottom;
    }
    #input {
        background: #16213e;
        color: #00d4aa;
        border: solid #0f3460;
    }
    #status-bar {
        height: 1;
        background: #16213e;
        color: #666666;
        text-align: center;
        dock: bottom;
    }
    .success { color: #00d4aa; }
    .error { color: #ff4444; }
    .info { color: #ffa500; }
    .dim { color: #666666; }
    """

    current_agent = reactive("researcher")
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="output", highlight=True, markup=True, wrap=True, max_lines=2000)
        with Container(id="input-container"):
            yield Input(id="input", placeholder="Type a command or question...")
        yield Static(id="status-bar")

    def on_mount(self) -> None:
        self.query_one("#input", Input).focus()
        self._load_session()
        self._discover_skills()
        self._banner()
        self._update_status()
        from core.cost_tracker import CostTracker
        self.cost_tracker = CostTracker()

    def _banner(self):
        out = self.query_one("#output", RichLog)
        out.write(f"[bold #00d4aa]{BRAND}[/bold #00d4aa]  [dim #666666]v2.0[/dim #666666]")
        out.write("[dim #666666]\u2500" * 50 + "[/dim #666666]")
        agent = AGENTS[self.current_agent]
        out.write(f"[dim #666666]Agent: {agent['label']} | {self.provider}/{self.model}[/dim #666666]")
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
        bar = self.query_one("#status-bar", Static)
        bar.update(f"  {agent['emoji']} {agent['label']}  |  {self.provider}/{self.model}  |  {BRAND}")

    def action_research(self, topic: str):
        out = self.query_one("#output", RichLog)
        from agents.researcher.agent import ResearcherAgent
        out.write(f"\n[bold #ffa500]=== RESEARCH ===[/bold #ffa500]  {topic}")
        a = ResearcherAgent()
        r = a.research(topic)
        for lens in ["technical", "business", "risks", "future", "actionable"]:
            text = r.get("analyses", {}).get(lens) or r.get(lens, "")
            if not text or text.startswith("Error"):
                out.write(f"  [bold #ff4444]\u2718 {lens.upper()}: error[/bold #ff4444]")
                continue
            out.write(f"\n  [bold #00d4aa]\u25B6 {lens.upper()}[/bold #00d4aa]")
            for line in text.strip().split("\n")[:6]:
                out.write(f"    {line[:120]}")

    @work(thread=True)
    def action_plan(self, description: str):
        from agents.orchestrator.agent import OrchestratorAgent
        out = self.query_one("#output", RichLog)
        out.write(f"\n[bold #ffa500]=== PLAN ===[/bold #ffa500]  {description}")
        o = OrchestratorAgent()
        result = o.run_pipeline(description)
        for s in result.get("stages", []):
            name = s["name"]
            status = s["status"]
            output = s.get("output", "")
            if status == "done":
                out.write(f"  [bold #00d4aa]\u2713 {name.upper()}[/bold #00d4aa]  [dim #666666]{output}[/dim #666666]")
            else:
                out.write(f"  [bold #ff4444]\u2718 {name.upper()}[/bold #ff4444]  [dim #666666]{s.get('error', 'failed')}[/dim #666666]")
        if result.get("all_passed"):
            out.write(f"\n  [bold #00d4aa]\u2713 Plan complete[/bold #00d4aa]")
        else:
            out.write(f"\n  [bold #ff4444]\u2718 Plan failed at: {result.get('failed_at')}[/bold #ff4444]")

    @work(thread=True)
    def action_tool(self, task: str):
        from core.tool_runner import ToolRunner
        out = self.query_one("#output", RichLog)
        out.write(f"\n[bold #ffa500]=== TOOL ===[/bold #ffa500]  {task}")
        runner = ToolRunner()
        result = runner.run(
            "You are an AI assistant with tool access. Use tools to accomplish the task.",
            task, agent="tool_user",
        )
        for line in result.split("\n")[:30]:
            out.write(f"  {line[:160]}")

    def action_review(self, filepath: str):
        out = self.query_one("#output", RichLog)
        from agents.reviewer.agent import ReviewerAgent
        if not os.path.exists(filepath):
            out.write(f"  [bold #ff4444]File not found: {filepath}[/bold #ff4444]")
        r = ReviewerAgent().review(filepath)
        for i in r.get("issues", []):
            sev = i.get("severity", "info")
            ln = i.get("line", "?")
            cl = {"error": "#ff4444", "warn": "#ffa500", "info": "#666666"}.get(sev, "#666666")
            out.write(f"  [{cl}][{sev.upper()}][L{ln}] {i.get('message', '')}[/{cl}]")
        s = r.get("summary", "")
        if s:
            out.write(f"  [dim #666666]{s[:200]}[/dim #666666]")

    def action_code(self, filepath: str, instructions: str):
        out = self.query_one("#output", RichLog)
        from agents.coder.agent import CodingAgent
        r = CodingAgent().modify(filepath, instructions)
        if r.get("success"):
            out.write(f"  [bold #00d4aa]\u2713 Modified {filepath}[/bold #00d4aa]")
        else:
            out.write(f"  [bold #ff4444]\u2718 {r.get('error', 'Failed')}[/bold #ff4444]")

    def action_generate(self, spec: str):
        out = self.query_one("#output", RichLog)
        from agents.coder.agent import CodingAgent
        lang = "python"
        if " --lang " in spec:
            parts = spec.split(" --lang ", 1)
            spec, lang = parts[0], parts[1].strip() or "python"
        r = CodingAgent().generate(spec, lang)
        if r.get("success"):
            code = r["code"]
            out.write(f"  [bold #00d4aa]\u2713 Generated {lang} code:[/bold #00d4aa]")
            for line in code.split("\n")[:20]:
                out.write(f"    {line}")
        else:
            out.write(f"  [bold #ff4444]\u2718 {r.get('error', 'Failed')}[/bold #ff4444]")

    def action_status(self):
        out = self.query_one("#output", RichLog)
        s = self.cost_tracker.summary()
        out.write(f"\n  [bold #ffa500]Session Status[/bold #ffa500]")
        out.write(f"    Calls:  {s['calls']}")
        out.write(f"    Tokens: {s['tokens']['total']}  (in: {s['tokens']['input']}  out: {s['tokens']['output']})")
        out.write(f"    Cost:   ${s['session_cost']}")
        out.write(f"    [dim #666666]Provider: {self.provider} | Model: {self.model}[/dim #666666]")

    def action_git(self, sub: str):
        out = self.query_one("#output", RichLog)
        import core.git_tools as git
        if not git.is_repo():
            out.write("  [bold #ff4444]Not a git repository[/bold #ff4444]")
            return
        if sub == "status" or not sub:
            out.write(f"\n  [bold #ffa500]Git Status[/bold #ffa500]\n  " + git.status().replace("\n", "\n  "))
        elif sub == "log":
            out.write(f"\n  [bold #ffa500]Git Log[/bold #ffa500]\n  " + git.log(10).replace("\n", "\n  "))
        elif sub == "branch":
            out.write(f"\n  [bold #ffa500]Branches[/bold #ffa500]\n  " + "\n  ".join(git.branches()))
        elif sub.startswith("commit"):
            msg = sub.split(" ", 1)[1] if " " in sub else ""
            if not msg:
                msg = git.auto_commit_message()
                out.write(f"  [dim #666666]Auto message: {msg}[/dim #666666]")
            r = git.commit(msg)
            if r["success"]:
                out.write(f"  [bold #00d4aa]\u2713 {r['output']}[/bold #00d4aa]")
            else:
                out.write(f"  [bold #ff4444]\u2718 {r['output']}[/bold #ff4444]")
        elif sub.startswith("switch") or sub.startswith("checkout"):
            branch_name = sub.split(" ", 1)[1] if " " in sub else ""
            if not branch_name:
                out.write("  Usage: /git switch <branch>")
                return
            r = git.switch(branch_name)
            if r["success"]:
                out.write(f"  [bold #00d4aa]\u2713 Switched to {branch_name}[/bold #00d4aa]")
            else:
                out.write(f"  [bold #ff4444]\u2718 {r['output']}[/bold #ff4444]")
        elif sub == "diff":
            out.write(f"\n  [bold #ffa500]Git Diff[/bold #ffa500]\n  " + git.diff().replace("\n", "\n  "))
        else:
            out.write(f"  [dim #666666]Subcommands: status, log, branch, commit, switch, diff[/dim #666666]")

    def action_project(self):
        out = self.query_one("#output", RichLog)
        from core.project_awareness import summary_text
        out.write(f"\n  [bold #ffa500]Project Overview[/bold #ffa500]\n  " + summary_text().replace("\n", "\n  "))

    def action_skills(self):
        out = self.query_one("#output", RichLog)
        if not self.skills:
            out.write("  [dim #666666]No skills discovered.[/dim #666666]")
            return
        out.write(f"\n  [bold #ffa500]Available Skills ({len(self.skills)})[/bold #ffa500]")
        for name in self.skills:
            out.write(f"    [bold #ffa500]/{name}[/bold #ffa500]")

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
            out.write(f"  [bold #ff4444]Unknown skill: {name}[/bold #ff4444]")
            return
        content = open(found, encoding="utf-8").read()[:2000]
        client = LLMClient()
        sys_prompt = f"CRITICAL: Produce the EXACT requested output directly — no disclaimers, no explanations.\n\n{content}"
        user_msg = extra or f"Apply the {name} skill and produce the output."
        r = client.chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ], agent="skill")
        out.write(f"\n  [bold #ffa500]\u2699\uFE0F Skill: {name}[/bold #ffa500]")
        for line in r.split("\n")[:40]:
            out.write(f"  {line[:160]}")

    def action_clear(self):
        self.query_one("#output", RichLog).clear()
        self._banner()

    def action_help(self):
        out = self.query_one("#output", RichLog)
        out.write(f"\n  [bold #ffa500]Commands[/bold #ffa500]")
        out.write(f"    [bold #ffa500]/research[/bold #ffa500] [dim #666666]<topic>[/dim #666666]")
        out.write(f"    [bold #ffa500]/plan[/bold #ffa500] [dim #666666]<desc>[/dim #666666]")
        out.write(f"    [bold #ffa500]/tool[/bold #ffa500] [dim #666666]<task>[/dim #666666]")
        out.write(f"    [bold #ffa500]/review[/bold #ffa500] [dim #666666]<file>[/dim #666666]")
        out.write(f"    [bold #ffa500]/code[/bold #ffa500] [dim #666666]<file> <desc>[/dim #666666]")
        out.write(f"    [bold #ffa500]/generate[/bold #ffa500] [dim #666666]<spec>[/dim #666666]")
        out.write(f"    [bold #ffa500]/agent[/bold #ffa500] [dim #666666]<name>[/dim #666666]")
        out.write(f"    [bold #ffa500]/git[/bold #ffa500] [dim #666666]status|log|commit|branch|switch|diff[/dim #666666]")
        out.write(f"    [bold #ffa500]/project[/bold #ffa500]")
        out.write(f"    [bold #ffa500]/skills[/bold #ffa500]")
        out.write(f"    [bold #ffa500]/status[/bold #ffa500]")
        out.write(f"    [bold #ffa500]/clear[/bold #ffa500]")
        out.write(f"    [bold #ffa500]/help[/bold #ffa500]")
        out.write(f"    [bold #ffa500]/exit[/bold #ffa500]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        inp = event.value.strip()
        self.query_one("#input", Input).clear()
        if not inp:
            return
        out = self.query_one("#output", RichLog)
        out.write(f"\n[dim #666666]\u2500[/dim #666666]" * 50)
        if inp.startswith("/"):
            parts = inp[1:].strip().split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1].strip() if len(parts) > 1 else ""
            if cmd == "research":
                if not args: out.write("  Usage: /research <topic>"); return
                self.action_research(args)
            elif cmd == "plan":
                if not args: out.write("  Usage: /plan <desc>"); return
                self.action_plan(args)
            elif cmd == "tool":
                if not args: out.write("  Usage: /tool <task>"); return
                self.action_tool(args)
            elif cmd == "review":
                if not args: out.write("  Usage: /review <file>"); return
                self.action_review(args)
            elif cmd == "code":
                ps = args.split(" ", 1)
                if len(ps) < 2: out.write("  Usage: /code <file> <instr>"); return
                self.action_code(ps[0], ps[1])
            elif cmd == "generate":
                if not args: out.write("  Usage: /generate <spec>"); return
                self.action_generate(args)
            elif cmd == "agent":
                if args and args.lower() in AGENTS:
                    self.current_agent = args.lower()
                    out.write(f"  [bold #00d4aa]Switched to {AGENTS[self.current_agent]['label']}[/bold #00d4aa]")
                    self._update_status()
                else:
                    out.write(f"  [dim #666666]Agents: {', '.join(AGENTS.keys())}[/dim #666666]")
            elif cmd == "git":
                self.action_git(args)
            elif cmd == "project":
                self.action_project()
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
                out.write(f"  [bold #ff4444]Unknown: /{cmd}[/bold #ff4444]  [dim #666666]/help[/dim #666666]")
        else:
            sk = self._find_skill(inp.split(" ")[0])
            if sk:
                parts = inp.strip().split(" ", 1)
                self.action_skill(sk, parts[1].strip() if len(parts) > 1 else "")
            else:
                self.action_research(inp)
        out.write(f"[dim #666666]\u2500[/dim #666666]" * 50)
        self._save_session()

    def _find_skill(self, name: str):
        for s in self.skills:
            if s.lower() == name.lower():
                return s
        return None

    def watch_current_agent(self, value):
        self._update_status()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.value.startswith("/"):
            self._show_completions(event.value)

    def _show_completions(self, text):
        pass

    def on_unmount(self):
        self._save_session()

def main():
    app = BrijeshAI()
    app.run()

if __name__ == "__main__":
    main()
