"""Brijesh'AI — Premium Interactive TUI"""
import sys, os
from glob import glob
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from core.llm_client import _load_env, LLMClient
from core.cost_tracker import CostTracker

_load_env()

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session.json")

def _save_session():
    try:
        with open(SESSION_FILE, "w") as f:
            __import__("json").dump({"current_agent": current_agent,
                "timestamp": __import__("datetime").datetime.now().isoformat()}, f)
    except: pass

def _load_session():
    if not os.path.exists(SESSION_FILE): return None
    try:
        with open(SESSION_FILE) as f:
            return __import__("json").load(f)
    except: return None

BRAND = "Brijesh'AI"
AGENTS = {
    "researcher": {"label": "Researcher", "emoji": "\U0001F50D"},
    "coder":      {"label": "Coder",      "emoji": "\U0001F4BB"},
    "reviewer":   {"label": "Reviewer",   "emoji": "\U0001F50D"},
    "tester":     {"label": "Tester",     "emoji": "\u2699\uFE0F"},
}

current_agent = "researcher"
provider = os.getenv("LLM_PROVIDER", "openai")
model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
DISCOVERED_SKILLS = []

COMMANDS = ["research", "review", "code", "generate", "test", "plan", "tool", "agent",
            "git", "project", "plugins", "status", "help", "clear", "exit", "quit",
            "skills", "skill", "agents"]

# --- Premium color palette ---
STYLE = Style.from_dict({
    "brand":     "#00e5bf bold",
    "accent":    "#ffb347 bold",
    "success":   "#98c379 bold",
    "error":     "#ff6b6b bold",
    "dim":       "#6b6b8a italic",
    "white":     "#e8e8f0",
    "toolbar":   "bg:#1a1a2a #6b6b8a",
    "prompt":    "#00e5bf bold",
    "header-bg": "bg:#12122a #e8e8f0",
})

bindings = KeyBindings()

@bindings.add("c-c")
def _(event): raise KeyboardInterrupt

@bindings.add("c-d")
def _(event): event.app.exit()

@bindings.add("tab")
def _(event):
    b = event.app.current_buffer
    if b.text.startswith("/"):
        b.start_completion(select_first=False)

class SlashCompleter(Completer):
    def __init__(self, words): self.words = words
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"): return
        partial = text[1:].lower()
        for word in self.words:
            if partial in word.lower():
                yield Completion("/" + word, start_position=-len(text), display="/" + word)

def p(text=""):
    if text:
        print_formatted_text(HTML(text), style=STYLE)
    else:
        print()

def banner():
    w = os.get_terminal_size().columns
    print()
    p(f"<brand>{BRAND}</brand>  <dim>v2.0</dim>")
    p(f"<dim>{'\u2500' * min(w - 2, 60)}</dim>")
    p(f"<dim>agent: {AGENTS[current_agent]['label']}  |  {provider}/{model}</dim>")
    p()

def sep():
    w = os.get_terminal_size().columns
    p(f"<dim>{'\u2500' * min(w - 2, 60)}</dim>")

# --- Action handlers ---

def do_research(topic):
    from agents.researcher.agent import ResearcherAgent
    from agents.researcher.prompts import SECTORS_ORDER
    enriched = f"Research topic: {topic}"
    a = ResearcherAgent()
    r = a.research(enriched)
    if r.get("type") == "general":
        answer = r.get("answer", "")
        if answer:
            for line in answer.split("\n"):
                print(f"  {line[:200]}")
        return
    sectors = r.get("sectors", {})
    for sector in SECTORS_ORDER:
        text = sectors.get(sector, "")
        if not text or text.startswith("Error"):
            p(f"  <dim>{sector}</dim>  <error>\u2718</error>")
            continue
        p(f"  <dim>{sector}</dim>  <success>\u2713</success>")
        first = text.strip().split("\n")[0][:120]
        if first:
            print(f"    {first}")

def do_plan(description):
    from agents.orchestrator.agent import OrchestratorAgent
    p(f"<accent>plan:</accent> {description}")
    result = OrchestratorAgent().run_pipeline(description)
    for s in result.get("stages", []):
        name = s["name"]; status = s["status"]; output = s.get("output", "")
        icon = "\u2713" if status == "done" else "\u2718"
        cl = "success" if status == "done" else "error"
        p(f"  <{cl}>{icon}</{cl}> <dim>{name}  {output}</dim>")
    if result.get("type") == "general":
        answer = result.get("results", {}).get("research", {}).get("answer", "")
        if answer:
            for line in answer.split("\n"):
                print(f"  {line[:200]}")
        return
    if result.get("all_passed"):
        report = result.get("results", {}).get("report", "")
        p(f"  <dim>{'\u2500' * 50}</dim>")
        p(f"  <accent>report</accent>  <dim>order code \u2192 /code or /generate</dim>")
        if report:
            for line in report.split("\n"):
                print(f"  {line[:200]}")
    else:
        p(f"  <error>\u2718 {result.get('failed_at')}</error>")

def do_tool(task):
    from core.tool_runner import ToolRunner
    p(f"<accent>tool:</accent> {task}")
    result = ToolRunner().run(
        "You are an AI assistant with tool access. Use tools to accomplish the task.",
        task, agent="tool_user")
    for line in result.split("\n")[:30]:
        print(f"  {line[:200]}")

def do_review(fp):
    from agents.reviewer.agent import ReviewerAgent
    p(f"<accent>review:</accent> {fp}")
    if not os.path.exists(fp):
        p(f"  <error>not found: {fp}</error>")
        return
    r = ReviewerAgent().review(fp)
    for i in r.get("issues", []):
        sev = i.get("severity", "error"); ln = i.get("line", "?")
        cl = "error" if sev == "error" else "accent" if sev == "warn" else "dim"
        p(f"  <{cl}>[{sev}][L{ln}] {i.get('message','')}</{cl}>")
    s = r.get("summary", "")
    if s:
        p(f"  <dim>{s[:200]}</dim>")

def do_code(fp, instr):
    from agents.coder.agent import CodingAgent
    p(f"<accent>code:</accent> {fp}")
    r = CodingAgent().modify(fp, instr)
    if r.get("success"):
        p(f"  <success>\u2713 modified</success>")
    else:
        p(f"  <error>\u2718 {r.get('error','Failed')}</error>")

def do_generate(spec, lang="python"):
    from agents.coder.agent import CodingAgent
    p(f"<accent>generate:</accent> {lang}")
    r = CodingAgent().generate(spec, lang)
    if r.get("success"):
        p(f"  <success>\u2713 generated</success>")
        for line in r["code"].split("\n")[:20]:
            print(f"  {line}")
    else:
        p(f"  <error>\u2718 {r.get('error','Failed')}</error>")

def do_status():
    s = CostTracker().summary()
    p(f"<accent>status</accent>")
    print(f"  calls:  {s['calls']}")
    print(f"  tokens: {s['tokens']['total']}  (in: {s['tokens']['input']}  out: {s['tokens']['output']})")
    p(f"  cost:   <accent>${s['session_cost']}</accent>")
    p(f"  <dim>model: {provider}/{model}</dim>")

def do_skills():
    if not DISCOVERED_SKILLS:
        p(f"  <dim>no skills discovered</dim>")
        return
    p(f"<accent>skills ({len(DISCOVERED_SKILLS)})</accent>")
    for s in DISCOVERED_SKILLS:
        p(f"  <accent>/{s['name']}</accent>  <dim>{s['description'][:80]}</dim>")

def do_skill(name, extra=""):
    for s in DISCOVERED_SKILLS:
        if s['name'].lower() == name.lower():
            p(f"<accent>skill:</accent> {s['name']}")
            client = LLMClient()
            sys_prompt = f"CRITICAL: Produce the EXACT requested output directly. No disclaimers.\n\n{s['content']}"
            user_msg = extra or f"Apply the {s['name']} skill."
            r = client.chat([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg}], agent="skill")
            for line in r.split("\n")[:40]:
                print(f"  {line[:200]}")
            return
    p(f"  <error>unknown skill: {name}</error>")

def do_git(sub):
    import core.git_tools as git
    p(f"<accent>git:</accent> {sub if sub else 'status'}")
    if not git.is_repo():
        p(f"  <error>not a git repo</error>")
        return
    if sub == "status" or not sub:
        for line in git.status().split("\n"):
            p(f"  <dim>{line}</dim>")
    elif sub == "log":
        for line in git.log(10).split("\n"):
            p(f"  <dim>{line}</dim>")
    elif sub == "branch":
        for b in git.branches():
            p(f"  <dim>{b}</dim>")
    elif sub.startswith("commit"):
        msg = sub.split(" ", 1)[1] if " " in sub else ""
        if not msg:
            msg = git.auto_commit_message()
            p(f"  <dim>auto: {msg}</dim>")
        r = git.commit(msg)
        p(f"  <{'success' if r['success'] else 'error'}>{r['output']}</{'success' if r['success'] else 'error'}>")
    elif sub.startswith("switch"):
        bn = sub.split(" ", 1)[1] if " " in sub else ""
        if not bn: p("  <dim>usage: /git switch <branch></dim>"); return
        r = git.switch(bn)
        p(f"  <{'success' if r['success'] else 'error'}>{r['output']}</{'success' if r['success'] else 'error'}>")
    elif sub == "diff":
        for line in git.diff().split("\n"):
            p(f"  <dim>{line}</dim>")
    else:
        p("  <dim>sub: status|log|branch|commit|switch|diff</dim>")

def do_project():
    from core.project_awareness import summary_text
    p(f"<accent>project</accent>")
    for line in summary_text().split("\n"):
        p(f"  <dim>{line}</dim>")

def do_plugins():
    from core.plugin_manager import get_registry
    reg = get_registry()
    p(f"<accent>plugins</accent>")
    if not reg.commands and not reg.agents:
        p("  <dim>none loaded</dim>")
        return
    for name, info in reg.commands.items():
        p(f"  <accent>/{name}</accent>  <dim>{info['description']}</dim>")
    for name, info in reg.agents.items():
        p(f"  <accent>{name}</accent> agent  <dim>{info['description']}</dim>")

def do_agents():
    p(f"<accent>agents</accent>")
    for k, v in AGENTS.items():
        p(f"  {v['emoji']} <accent>{k}</accent>  <dim>{v['label']}</dim>")

def do_help():
    p(f"<accent>commands</accent>")
    p("  <dim>/research</dim>  <dim>&lt;topic&gt;</dim>")
    p("  <dim>/plan</dim>      <dim>&lt;desc&gt;</dim>    research 11 sectors + report")
    p("  <dim>/tool</dim>      <dim>&lt;task&gt;</dim>    tool-using agent")
    p("  <dim>/review</dim>    <dim>&lt;file&gt;</dim>")
    p("  <dim>/code</dim>      <dim>&lt;file&gt; &lt;instr&gt;</dim>")
    p("  <dim>/generate</dim>  <dim>&lt;spec&gt;</dim>")
    p("  <dim>/agent</dim>     <dim>&lt;name&gt;</dim>")
    p("  <dim>/git</dim>       <dim>status|log|commit|branch|switch|diff</dim>")
    p("  <dim>/project</dim>")
    p("  <dim>/plugins</dim>   <dim>/skills</dim>   <dim>/status</dim>   <dim>/clear</dim>   <dim>/exit</dim>")

def _find_skill(topic):
    for s in DISCOVERED_SKILLS:
        if s['name'].lower() == topic.lower(): return s
    return None

COMMANDS_MAP = {
    "research": lambda a: do_research(a) if a else None,
    "review":   lambda a: do_review(a) if a else None,
    "code":     lambda a: exec('ps=a.split(" ",1); do_code(ps[0],ps[1]) if len(ps)>=2 else None'),
    "generate": lambda a: do_generate(a) if a else None,
    "plan":     lambda a: do_plan(a) if a else None,
    "tool":     lambda a: do_tool(a) if a else None,
    "git":      lambda a: do_git(a),
    "project":  lambda a: do_project(),
    "plugins":  lambda a: do_plugins(),
    "agent":    lambda a: switch_agent(a),
    "skills":   lambda a: do_skills(),
    "skill":    lambda a: do_skill(*(a.split(" ", 1)+[""])[:2]),
    "status":   lambda a: do_status(),
    "help":     lambda a: do_help(),
    "clear":    lambda a: os.system("cls" if os.name=="nt" else "clear") or banner(),
    "exit":     lambda a: sys.exit(0),
    "quit":     lambda a: sys.exit(0),
}

def switch_agent(name):
    global current_agent
    if name and name.lower() in AGENTS:
        current_agent = name.lower()
        p(f"  <success>switched to {AGENTS[current_agent]['label']}</success>")
    else:
        p(f"  <dim>agents: {', '.join(AGENTS.keys())}</dim>")

def run(cmd, args):
    fn = COMMANDS_MAP.get(cmd.lower())
    if fn:
        try: fn(args)
        except: pass
    else:
        from core.plugin_manager import get_registry
        reg = get_registry()
        if cmd in reg.commands:
            for line in reg.commands[cmd]["handler"](args).split("\n"):
                print(f"  {line}")
        else:
            p(f"  <error>unknown: /{cmd}</error>  <dim>/help</dim>")

def toolbar():
    ai = AGENTS[current_agent]
    try:
        import core.git_tools as git
        branch = git.branch() if git.is_repo() else ""
    except:
        branch = ""
    parts = [f" {ai['emoji']} {ai['label']}  |  {provider}/{model}"]
    if branch:
        parts.append(f"  {branch}")
    c = CostTracker().summary()
    parts.append(f"  ${c['session_cost']:.4f}")
    return HTML("  " + "  |".join(parts) + f"  |  {BRAND}")

def main():
    global current_agent, DISCOVERED_SKILLS
    os.system("cls" if os.name == "nt" else "clear")
    banner()
    DISCOVERED_SKILLS = discover_skills() + discover_skills_from_openpai()
    prev = _load_session()
    if prev:
        current_agent = prev.get("current_agent", current_agent)
        ts = prev.get("timestamp", "?")[:19]
        p(f"  <dim>resuming session from {ts}</dim>")
    session = PromptSession(
        history=FileHistory(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tui_history")),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
        style=STYLE,
    )
    while True:
        try:
            inp = session.prompt(
                HTML(f"<prompt>{AGENTS[current_agent]['emoji']} {BRAND} > </prompt>"),
                bottom_toolbar=toolbar,
                style=STYLE,
                completer=SlashCompleter(COMMANDS),
                complete_while_typing=True,
            )
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        inp = inp.strip()
        if not inp: continue
        sep()
        if inp.startswith("/"):
            ps = inp[1:].strip().split(" ", 1)
            run(ps[0].lower(), ps[1].strip() if len(ps) > 1 else "")
        else:
            sk = _find_skill(inp.split(" ")[0])
            if sk:
                ps = inp.strip().split(" ", 1)
                do_skill(sk['name'], ps[1].strip() if len(ps) > 1 else "")
            else:
                do_research(inp)
        sep()
    _save_session()
    p("\n  <dim>goodbye!</dim>\n")

def discover_skills():
    dirs = [os.path.expanduser("~/.config/opencode/skills"), os.path.expanduser("~/.agents/skills")]
    found, seen = [], set()
    for d in dirs:
        for f in glob(os.path.join(d, "**/SKILL.md"), recursive=True):
            name = Path(f).parent.name
            if name not in seen:
                seen.add(name)
                try:
                    txt = open(f, encoding="utf-8").read()[:200]
                    found.append({"name": name, "path": f, "description": txt.strip()[:200], "content": txt[:2000]})
                except: pass
    return found

def discover_skills_from_openpai():
    return []

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: _save_session(); p("\n  <dim>goodbye!</dim>\n")
    except Exception as e: _save_session(); p(f"\n  <error>fatal: {e}</error>\n")
