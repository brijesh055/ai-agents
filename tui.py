"""Brijesh'AI — Premium Interactive TUI"""
import sys, os, textwrap, json
from glob import glob
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from core.llm_client import _load_env, LLMClient
from core.cost_tracker import CostTracker

_load_env()

# --- ANSI color codes (works on Windows 10+ / Terminal / PowerShell) ---
C = {
    "teal":   "\033[38;2;0;229;191m",
    "amber":  "\033[38;2;255;179;71m",
    "green":  "\033[38;2;152;195;121m",
    "red":    "\033[38;2;255;107;107m",
    "gray":   "\033[38;2;107;107;138m",
    "white":  "\033[38;2;232;232;240m",
    "bold":   "\033[1m",
    "italic": "\033[3m",
    "dim":    "\033[2m",
    "reset":  "\033[0m",
}

def clr(code, text):
    return f"{C[code]}{text}{C['reset']}"

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".session.json")

def _save_session():
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"current_agent": current_agent,
                "timestamp": __import__("datetime").datetime.now().isoformat()}, f)
    except: pass

def _load_session():
    if not os.path.exists(SESSION_FILE): return None
    try:
        with open(SESSION_FILE) as f: return json.load(f)
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

COMMANDS = ["research","review","code","generate","test","plan","tool","agent",
            "git","project","plugins","status","help","clear","exit","quit","skills","skill","agents"]

PT_STYLE = Style.from_dict({
    "prompt":  "#00e5bf bold",
    "toolbar": "bg:#1a1a2a #6b6b8a",
})

bindings = KeyBindings()
@bindings.add("c-c")
def _(event): raise KeyboardInterrupt
@bindings.add("c-d")
def _(event): event.app.exit()
@bindings.add("tab")
def _(event):
    b = event.app.current_buffer
    if b.text.startswith("/"): b.start_completion(select_first=False)

class SlashCompleter(Completer):
    def __init__(self, words): self.words = words
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"): return
        partial = text[1:].lower()
        for word in self.words:
            if partial in word.lower():
                yield Completion("/" + word, start_position=-len(text), display="/" + word)

def cols():
    try: return os.get_terminal_size().columns
    except: return 80

def hr():  # horizontal rule
    c = cols()
    print(clr("gray", "\u2500" * min(c - 2, 60)))

def wrap(text, indent=2, width=0):
    c = cols()
    w = width or (c - indent - 2)
    for line in text.split("\n"):
        for chunk in textwrap.wrap(line, width=w) or [""]:
            yield (" " * indent) + chunk

def banner():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except: pass
    print()
    print(f"  {clr('teal', BRAND)}  {clr('gray', 'v2.0')}")
    hr()
    print(f"  {clr('gray', 'agent: ' + AGENTS[current_agent]['label'] + '  |  ' + provider + '/' + model)}")
    print()

# --- Handlers ---

def do_research(topic):
    from agents.researcher.agent import ResearcherAgent
    from agents.researcher.prompts import SECTORS_ORDER
    r = ResearcherAgent().research(topic)
    if r.get("type") == "general":
        for line in wrap(r.get("answer", ""), indent=2):
            print(line[:200])
        return
    sectors = r.get("sectors", {})
    for sector in SECTORS_ORDER:
        text = sectors.get(sector, "")
        if not text or text.startswith("Error"):
            print(f"  {clr('gray', sector)}  {clr('red', '\u2718')}")
            continue
        print(f"  {clr('gray', sector)}  {clr('green', '\u2713')}")
        first = text.strip().split("\n")[0][:150]
        if first:
            for l in wrap(first, indent=4):
                print(l)

def do_plan(description):
    from agents.orchestrator.agent import OrchestratorAgent
    print(f"  {clr('amber', 'plan:')} {description}")
    result = OrchestratorAgent().run_pipeline(description)
    for s in result.get("stages", []):
        icon = "\u2713" if s["status"] == "done" else "\u2718"
        col = "green" if s["status"] == "done" else "red"
        print(f"  {clr(col, icon)} {clr('gray', s['name'] + '  ' + s.get('output',''))}")
    if result.get("type") == "general":
        for line in wrap(result.get("results",{}).get("research",{}).get("answer",""), indent=2):
            print(line[:200])
        return
    if result.get("all_passed"):
        report = result.get("results",{}).get("report","")
        hr()
        print(f"  {clr('amber', 'report')}  {clr('gray', 'order code \u2192 /code or /generate')}")
        if report:
            for line in report.split("\n"):
                for l in wrap(line, indent=2):
                    print(l[:200])
    else:
        print(f"  {clr('red', '\u2718 ' + str(result.get('failed_at','')))}")

def do_tool(task):
    from core.tool_runner import ToolRunner
    print(f"  {clr('amber', 'tool:')} {task}")
    result = ToolRunner().run("You are an AI assistant with tool access.", task, agent="tool_user")
    for line in result.split("\n")[:30]:
        for l in wrap(line, indent=2):
            print(l[:200])

def do_review(fp):
    from agents.reviewer.agent import ReviewerAgent
    print(f"  {clr('amber', 'review:')} {fp}")
    if not os.path.exists(fp):
        print(f"  {clr('red', 'not found: ' + fp)}"); return
    r = ReviewerAgent().review(fp)
    for i in r.get("issues", []):
        sev=i.get("severity","error"); ln=i.get("line","?")
        col="red" if sev=="error" else "amber" if sev=="warn" else "gray"
        print(f"  {clr(col, '['+sev+'][L'+str(ln)+'] ' + i.get('message',''))}")
    if r.get("summary"):
        print(f"  {clr('gray', r['summary'][:200])}")

def do_code(fp, instr):
    from agents.coder.agent import CodingAgent
    print(f"  {clr('amber', 'code:')} {fp}")
    r=CodingAgent().modify(fp, instr)
    if r.get("success"):
        print(f"  {clr('green', '\u2713 modified')}")
    else:
        print(f"  {clr('red', '\u2718 ' + r.get('error','Failed'))}")

def do_generate(spec, lang="python"):
    from agents.coder.agent import CodingAgent
    print(f"  {clr('amber', 'generate:')} {lang}")
    r=CodingAgent().generate(spec, lang)
    if r.get("success"):
        print(f"  {clr('green', '\u2713 generated')}")
        for line in r["code"].split("\n")[:20]:
            print(f"    {line[:200]}")
    else:
        print(f"  {clr('red', '\u2718 ' + r.get('error','Failed'))}")

def do_status():
    s=CostTracker().summary()
    print(f"  {clr('amber', 'status')}")
    print(f"    calls:  {s['calls']}")
    print(f"    tokens: {s['tokens']['total']}  (in: {s['tokens']['input']}  out: {s['tokens']['output']})")
    print(f"    cost:   {clr('amber', '$'+str(s['session_cost']))}")
    print(f"    {clr('gray', 'model: ' + provider + '/' + model)}")

def do_skills():
    if not DISCOVERED_SKILLS:
        print(f"  {clr('gray', 'no skills discovered')}"); return
    print(f"  {clr('amber', 'skills (' + str(len(DISCOVERED_SKILLS)) + ')')}")
    for s in DISCOVERED_SKILLS:
        print(f"  {clr('amber', '/' + s['name'])}  {clr('gray', s['description'][:80])}")

def do_skill(name, extra=""):
    for s in DISCOVERED_SKILLS:
        if s['name'].lower()==name.lower():
            print(f"  {clr('amber', 'skill:')} {s['name']}")
            r=LLMClient().chat([
                {"role":"system","content":f"CRITICAL: Produce EXACT output directly. No disclaimers.\n\n{s['content']}"},
                {"role":"user","content":extra or f"Apply the {s['name']} skill."}], agent="skill")
            for line in r.split("\n")[:40]:
                print(f"  {line[:200]}")
            return
    print(f"  {clr('red', 'unknown skill: ' + name)}")

def do_git(sub):
    import core.git_tools as git
    print(f"  {clr('amber', 'git:')} {sub if sub else 'status'}")
    if not git.is_repo():
        print(f"  {clr('red', 'not a git repo')}"); return
    if sub=="status" or not sub:
        for line in git.status().split("\n"): print(f"  {clr('gray', line)}")
    elif sub=="log":
        for line in git.log(10).split("\n"): print(f"  {clr('gray', line)}")
    elif sub=="branch":
        for b in git.branches(): print(f"  {clr('gray', b)}")
    elif sub.startswith("commit"):
        msg=sub.split(" ",1)[1] if " " in sub else ""
        if not msg: msg=git.auto_commit_message(); print(f"  {clr('gray', 'auto: ' + msg)}")
        r=git.commit(msg)
        col="green" if r["success"] else "red"
        print(f"  {clr(col, r['output'])}")
    elif sub.startswith("switch"):
        bn=sub.split(" ",1)[1] if " " in sub else ""
        if not bn: print(f"  {clr('gray', 'usage: /git switch <branch>')}"); return
        r=git.switch(bn)
        col="green" if r["success"] else "red"
        print(f"  {clr(col, r['output'])}")
    elif sub=="diff":
        for line in git.diff().split("\n"): print(f"  {clr('gray', line)}")
    else:
        print(f"  {clr('gray', 'sub: status|log|branch|commit|switch|diff')}")

def do_project():
    from core.project_awareness import summary_text
    print(f"  {clr('amber', 'project')}")
    for line in summary_text().split("\n"): print(f"  {clr('gray', line)}")

def do_plugins():
    from core.plugin_manager import get_registry
    reg=get_registry()
    print(f"  {clr('amber', 'plugins')}")
    if not reg.commands and not reg.agents:
        print(f"  {clr('gray', 'none loaded')}"); return
    for n,i in reg.commands.items(): print(f"  {clr('amber', '/'+n)}  {clr('gray', i['description'])}")
    for n,i in reg.agents.items(): print(f"  {clr('amber', n)} agent  {clr('gray', i['description'])}")

def do_agents():
    print(f"  {clr('amber', 'agents')}")
    for k,v in AGENTS.items(): print(f"  {v['emoji']} {clr('amber', k)}  {clr('gray', v['label'])}")

def do_help():
    print(f"  {clr('amber', 'commands')}")
    print(f"  {clr('gray', '/research')}  <topic>")
    print(f"  {clr('gray', '/plan')}      <desc>    11 sectors + report")
    print(f"  {clr('gray', '/tool')}      <task>    tool-using agent")
    print(f"  {clr('gray', '/review')}    <file>")
    print(f"  {clr('gray', '/code')}      <file> <instr>")
    print(f"  {clr('gray', '/generate')}  <spec>")
    print(f"  {clr('gray', '/agent')}     <name>")
    print(f"  {clr('gray', '/git')}       status|log|commit|branch|switch|diff")
    print(f"  {clr('gray', '/project')}  {clr('gray', '/plugins')}  {clr('gray', '/skills')}  {clr('gray', '/status')}")
    print(f"  {clr('gray', '/clear')}    {clr('gray', '/exit')}")

CMD = {
    "research": lambda a: do_research(a) if a else None,
    "review":   lambda a: do_review(a) if a else None,
    "code":     lambda a: (lambda ps: do_code(ps[0],ps[1]) if len(ps)>=2 else None)(a.split(" ",1)),
    "generate": lambda a: do_generate(a) if a else None,
    "plan":     lambda a: do_plan(a) if a else None,
    "tool":     lambda a: do_tool(a) if a else None,
    "git":      lambda a: do_git(a),
    "project":  lambda a: do_project(),
    "plugins":  lambda a: do_plugins(),
    "agent":    lambda a: _switch_agent(a),
    "skills":   lambda a: do_skills(),
    "skill":    lambda a: do_skill(*((a.split(" ",1)+[""])[:2])),
    "status":   lambda a: do_status(),
    "help":     lambda a: do_help(),
    "clear":    lambda a: banner(),
    "exit":     lambda a: sys.exit(0),
    "quit":     lambda a: sys.exit(0),
}

def _switch_agent(name):
    global current_agent
    if name and name.lower() in AGENTS:
        current_agent=name.lower()
        print(f"  {clr('green', 'switched to ' + AGENTS[current_agent]['label'])}")
    else:
        print(f"  {clr('gray', 'agents: ' + ', '.join(AGENTS.keys()))}")

def run(cmd, args):
    fn=CMD.get(cmd.lower())
    if fn:
        try: fn(args)
        except Exception as e: print(f"  {clr('red', 'error: ' + str(e))}")
    else:
        from core.plugin_manager import get_registry
        reg=get_registry()
        if cmd in reg.commands:
            for line in reg.commands[cmd]["handler"](args).split("\n"):
                print(f"  {line}")
        else:
            print(f"  {clr('red', 'unknown: /' + cmd)}  {clr('gray', '/help')}")

def toolbar():
    ai=AGENTS[current_agent]
    try:
        import core.git_tools as git
        branch=git.branch() if git.is_repo() else ""
    except: branch=""
    parts=[f" {ai['emoji']} {ai['label']}  |  {provider}/{model}"]
    if branch: parts.append(f"  {branch}")
    c=CostTracker().summary()
    parts.append(f"  ${c['session_cost']:.4f}")
    return HTML("  "+"  |".join(parts)+f"  |  {BRAND}")

def discover_skills():
    dirs=[os.path.expanduser("~/.config/opencode/skills"),os.path.expanduser("~/.agents/skills")]
    found,seen=[],set()
    for d in dirs:
        for f in glob(os.path.join(d,"**/SKILL.md"),recursive=True):
            name=Path(f).parent.name
            if name not in seen:
                seen.add(name)
                try:
                    txt=open(f,encoding="utf-8").read()[:200]
                    found.append({"name":name,"path":f,"description":txt.strip()[:200],"content":txt[:2000]})
                except: pass
    return found

def main():
    global current_agent, DISCOVERED_SKILLS
    banner()
    DISCOVERED_SKILLS=discover_skills()
    prev=_load_session()
    if prev:
        current_agent=prev.get("current_agent",current_agent)
        ts=prev.get("timestamp","?")[:19]
        print(f"  {clr('gray', 'resuming session from ' + ts)}")
    session=PromptSession(
        history=FileHistory(os.path.join(os.path.dirname(os.path.abspath(__file__)),".tui_history")),
        auto_suggest=AutoSuggestFromHistory(), enable_history_search=True, style=PT_STYLE)
    while True:
        try:
            inp=session.prompt(
                HTML(f"<prompt>{AGENTS[current_agent]['emoji']} {BRAND} > </prompt>"),
                bottom_toolbar=toolbar, style=PT_STYLE,
                completer=SlashCompleter(COMMANDS), complete_while_typing=True)
        except KeyboardInterrupt: continue
        except EOFError: break
        inp=inp.strip()
        if not inp: continue
        hr()
        if inp.startswith("/"):
            ps=inp[1:].strip().split(" ",1)
            run(ps[0].lower(), ps[1].strip() if len(ps)>1 else "")
        else:
            sk=_find_skill(inp.split(" ")[0])
            if sk:
                ps=inp.strip().split(" ",1)
                do_skill(sk['name'], ps[1].strip() if len(ps)>1 else "")
            else: do_research(inp)
        hr()
    _save_session()

def _find_skill(topic):
    for s in DISCOVERED_SKILLS:
        if s['name'].lower()==topic.lower(): return s
    return None

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: _save_session()
    except Exception as e: _save_session(); print(f"  {clr('red', 'fatal: ' + str(e))}")
