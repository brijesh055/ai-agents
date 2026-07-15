"""Brijesh'AI — Interactive TUI (like Claude Code / opencode)"""
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
    data = {
        "current_agent": current_agent,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    try:
        with open(SESSION_FILE, "w") as f:
            __import__("json").dump(data, f)
    except:
        pass

def _load_session():
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE) as f:
            data = __import__("json").load(f)
        return data
    except:
        return None

def _clear_session():
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except:
        pass

BRAND = "Brijesh'AI"

AGENTS = {
    "researcher": {"label": "Researcher", "emoji": "\U0001F50D"},
    "coder":      {"label": "Coder",      "emoji": "\U0001F4BB"},
    "reviewer":   {"label": "Reviewer",   "emoji": "\U0001F50D"},
    "tester":     {"label": "Tester",     "emoji": "\u2699\uFE0F"},
}

current_agent = "researcher"
provider = os.getenv("LLM_PROVIDER", "ollama")
model = os.getenv("LLM_MODEL", "qwen2.5:7b")

DISCOVERED_SKILLS = []

COMMANDS = ["research", "review", "code", "generate", "test", "plan", "agent", "status", "help", "clear", "exit", "quit", "skills", "skill", "agents"]

def _parse_skill(p):
    try:
        txt = open(p, encoding="utf-8").read()
        desc = ""
        lines = txt.split("\n")
        in_fm = lines and lines[0].strip() == "---"
        if in_fm:
            collecting = False
            collected = []
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if collecting:
                    if line.startswith("  ") or line.startswith("\t"):
                        collected.append(line.strip())
                    else:
                        break
                elif line.startswith("description:"):
                    v = line.split(":", 1)[1].strip()
                    if v == ">":
                        collecting = True
                    else:
                        desc = v.strip('"').strip("'")[:200]
                        break
            if collecting and collected:
                desc = " ".join(collected)[:200]
        if not desc:
            for line in lines:
                if line.strip() and not line.startswith("#") and not line.startswith("---"):
                    desc = line.strip()[:200]
                    break
        return {"name": Path(p).parent.name, "path": p, "description": desc, "content": txt[:2000]}
    except:
        return None

def discover_skills():
    dirs = [
        os.path.expanduser("~/.config/opencode/skills"),
        os.path.expanduser("~/.agents/skills"),
    ]
    found = []
    seen = set()
    for d in dirs:
        for f in glob(os.path.join(d, "**/SKILL.md"), recursive=True):
            s = _parse_skill(f)
            if s and s["name"] not in seen:
                seen.add(s["name"])
                found.append(s)
    return found

def discover_skills_from_openpai():
    skills_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")
    found = []
    seen = set()
    if os.path.isdir(skills_dir):
        for f in glob(os.path.join(skills_dir, "**/SKILL.md"), recursive=True):
            s = _parse_skill(f)
            if s and s["name"] not in seen:
                seen.add(s["name"])
                found.append(s)
    return found

pft = print_formatted_text
history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tui_history")

style = Style.from_dict({
    "header":  "#00d4aa bold",
    "brand":   "#ff6b9d bold",
    "cmd":     "#ffa500",
    "err":     "#ff4444",
    "ok":      "#00d4aa",
    "dim":     "#666666 italic",
    "toolbar": "bg:#222222 #aaaaaa",
    "prompt":  "bold #00d4aa",
})

bindings = KeyBindings()

@bindings.add("c-c")
def _(event):
    raise KeyboardInterrupt

@bindings.add("c-d")
def _(event):
    event.app.exit()

@bindings.add("tab")
def _(event):
    b = event.app.current_buffer
    if b.text.startswith("/"):
        b.start_completion(select_first=False)

class SlashCompleter(Completer):
    def __init__(self, words):
        self.words = words

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        partial = text[1:].lower()
        for word in self.words:
            if partial in word.lower():
                yield Completion(
                    "/" + word, start_position=-len(text), display="/" + word
                )

def p(*args, **kw):
    pft(HTML(" ".join(str(a) for a in args)), **kw)

def banner():
    w = os.get_terminal_size().columns
    print()
    p(f"<b><header>{BRAND}</header></b>  <dim>v1.0</dim>")
    p("<dim>" + "\u2500" * min(w - 2, 50) + "</dim>")
    p(f"<dim>Type /help for commands. Agent: {AGENTS[current_agent]['label']}</dim>")
    print()

def sep():
    w = os.get_terminal_size().columns
    p("<dim>" + "\u2500" * min(w - 2, 50) + "</dim>")

def do_research(topic):
    from agents.researcher.agent import ResearcherAgent
    ctx = f"Project context: available agents = {', '.join(AGENTS.keys())}. "
    if DISCOVERED_SKILLS:
        ctx += f"Available skills = {', '.join(s['name'] for s in DISCOVERED_SKILLS[:5])}. "
    enriched = f"{ctx}\nResearch topic: {topic}"
    a = ResearcherAgent()
    print(end="", flush=True)
    r = a.research(enriched)
    for lens in ["technical", "business", "risks", "future", "actionable"]:
        text = r.get("analyses", {}).get(lens) or r.get(lens, "")
        if not text or text.startswith("Error"):
            p(f"  <err>\u2718 {lens.upper()}: error</err>")
            continue
        p(f"\n  <cmd>\u25B6 {lens.upper()}</cmd>")
        for line in text.strip().split("\n")[:8]:
            print(f"    {line[:120]}")
    print()

def do_review(fp):
    from agents.reviewer.agent import ReviewerAgent
    if not os.path.exists(fp):
        p(f"  <err>File not found: {fp}</err>")
        return
    r = ReviewerAgent().review(fp)
    for i in r.get("issues", []):
        sev = i.get("severity", "info")
        ln = i.get("line", "?")
        cl = {"error": "err", "warn": "warn", "info": "dim"}.get(sev, "dim")
        p(f"  <{cl}>[{sev.upper()}][L{ln}] {i.get('message','')}</{cl}>")
    s = r.get("summary", "")
    if s:
        p(f"  <dim>{s[:200]}</dim>")
    print()

def do_code(fp, instr):
    from agents.coder.agent import CodingAgent
    r = CodingAgent().modify(fp, instr)
    if r.get("success"):
        p(f"  <ok>\u2713 Modified {fp}</ok>")
    else:
        p(f"  <err>\u2718 {r.get('error','Failed')}</err>")
    print()

def do_generate(spec, lang="python"):
    from agents.coder.agent import CodingAgent
    r = CodingAgent().generate(spec, lang)
    if r.get("success"):
        code = r["code"]
        p(f"  <ok>\u2713 Generated {lang} code:</ok>")
        for line in code.split("\n")[:20]:
            print(f"    {line}")
        if len(code.split("\n")) > 20:
            p(f"  <dim>... {len(code.split(chr(10))) - 20} more lines</dim>")
    else:
        p(f"  <err>\u2718 {r.get('error','Failed')}</err>")
    print()

def do_plan(description):
    from agents.orchestrator.agent import OrchestratorAgent
    p(f"  <cmd>=== PLAN ===</cmd>  {description}")
    print()
    o = OrchestratorAgent()
    result = o.run_pipeline(description)
    stages = result.get("stages", [])
    for s in stages:
        name = s["name"]
        status = s["status"]
        output = s.get("output", "")
        if status == "done":
            p(f"  <ok>\u2713 {name.upper()}</ok>  <dim>{output}</dim>")
        else:
            p(f"  <err>\u2718 {name.upper()}</err>  <dim>{s.get('error', 'failed')}</dim>")
    if result.get("all_passed"):
        print()
        p(f"  <ok>\u2713 Plan complete</ok>")
    else:
        print()
        p(f"  <err>\u2718 Plan failed at stage: {result.get('failed_at')}</err>")
    print()

def do_status():
    s = CostTracker().summary()
    p(f"  <cmd>Session Status</cmd>")
    print(f"    Calls:  {s['calls']}")
    print(f"    Tokens: {s['tokens']['total']}  (in: {s['tokens']['input']}  out: {s['tokens']['output']})")
    print(f"    Cost:   ${s['session_cost']}")
    p(f"    <dim>Provider: {provider} | Model: {model}</dim>")
    print()

def do_skills():
    if not DISCOVERED_SKILLS:
        p(f"  <dim>No skills discovered. Check ~/.config/opencode/skills/</dim>")
        print()
        return
    p(f"  <cmd>Available Skills ({len(DISCOVERED_SKILLS)})</cmd>")
    for s in DISCOVERED_SKILLS:
        p(f"    <cmd>/{s['name']}</cmd>  <dim>{s['description'][:80]}</dim>")
    print()

def do_skill(name, extra_args=""):
    for s in DISCOVERED_SKILLS:
        if s['name'].lower() == name.lower():
            print()
            p(f"  <cmd>\u2699\uFE0F Skill: {s['name']}</cmd>")
            print()
            client = LLMClient()
            sys_prompt = f"CRITICAL: Produce the EXACT requested output (code, design tokens, config, etc.) directly — no disclaimers, no explanations, no markdown wrappers unless specified. Output the deliverable itself, not a description of it.\n\n{s['content']}"
            user_msg = extra_args or f"Apply the {s['name']} skill to this project and produce the output."
            r = client.chat([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg},
            ], agent="skill")
            for line in r.split("\n")[:40]:
                print(f"  {line[:160]}")
            if len(r.split("\n")) > 40:
                p(f"  <dim>... {len(r.split('\n')) - 40} more lines</dim>")
            print()
            return
    p(f"  <err>Unknown skill: {name}</err>  <dim>Type /skills to list</dim>")
    print()

def _find_skill(topic):
    for s in DISCOVERED_SKILLS:
        if s['name'].lower() == topic.lower():
            return s
    return None

def do_agents():
    p(f"  <cmd>Available Agents</cmd>")
    for k, v in AGENTS.items():
        p(f"    {v['emoji']} <cmd>{k}</cmd>  <dim>{v['label']}</dim>")
    print()

def do_help():
    p(f"  <cmd>Commands</cmd>")
    p(f"    <cmd>/research</cmd> <dim>&lt;topic&gt;</dim>       Five-lens research")
    p(f"    <cmd>/review</cmd> <dim>&lt;file&gt;</dim>          Review code")
    p(f"    <cmd>/code</cmd> <dim>&lt;file&gt; &lt;desc&gt;</dim>  Modify code with AI")
    p(f"    <cmd>/generate</cmd> <dim>&lt;spec&gt;</dim>        Generate code")
    p(f"    <cmd>/plan</cmd> <dim>&lt;desc&gt;</dim>            Full pipeline: research → code → review → validate")
    p(f"    <cmd>/test</cmd> <dim>&lt;url&gt;</dim>             Web tests")
    p(f"    <cmd>/agent</cmd> <dim>&lt;name&gt;</dim>          Agent: {', '.join(AGENTS.keys())}")
    p(f"    <cmd>/agents</cmd>                    List specialized agents")
    p(f"    <cmd>/skills</cmd>                    List available skills")
    p(f"    <cmd>/skill</cmd> <dim>&lt;name&gt;</dim>          Load a skill")
    p(f"    <cmd>/status</cmd>                    Costs and stats")
    p(f"    <cmd>/help</cmd>                      This help")
    p(f"    <cmd>/clear</cmd>                     Clear screen")
    p(f"    <cmd>/exit</cmd>                      Quit")
    print()

def run(cmd, args):
    global current_agent
    c = cmd.lower()
    if c == "research":
        if not args: print("  Usage: /research <topic>"); return
        do_research(args)
    elif c == "review":
        if not args: print("  Usage: /review <file>"); return
        do_review(args)
    elif c == "code":
        ps = args.split(" ", 1)
        if len(ps) < 2: print("  Usage: /code <file> <instructions>"); return
        do_code(ps[0], ps[1])
    elif c == "generate":
        if not args: print("  Usage: /generate <spec>"); return
        lang = "python"
        if " --lang " in args:
            ps = args.split(" --lang ", 1)
            args, lang = ps[0], ps[1].strip() or "python"
        do_generate(args, lang)
    elif c == "test":
        if not args: print("  Usage: /test <url>"); return
        from agents.web_tester.agent import WebTestingAgent
        r = WebTestingAgent().run_test(args, [{"action": "navigate", "selector": args}])
        cl = "ok" if r.get("success") else "err"
        p(f"  <{cl}>Test {'ok' if r.get('success') else 'failed'}: {args}</{cl}>")
        for e in r.get("errors", []):
            p(f"  <err>  {e}</err>")
        print()
    elif c == "agent":
        if args and args.lower() in AGENTS:
            global current_agent
            current_agent = args.lower()
            ai = AGENTS[current_agent]
            p(f"  <ok>Switched to {ai['emoji']} {ai['label']}</ok>")
        else:
            p(f"  <dim>Agents: {', '.join(AGENTS.keys())}</dim>")
        print()
    elif c == "plan":
        if not args: print("  Usage: /plan <description>"); return
        do_plan(args)
    elif c == "status":
        do_status()
    elif c == "skills":
        do_skills()
    elif c == "skill":
        if not args: print("  Usage: /skill <name> [args]"); return
        ps = args.split(" ", 1)
        do_skill(ps[0], ps[1].strip() if len(ps) > 1 else "")
    elif c == "agents":
        do_agents()
    elif c == "help":
        do_help()
    elif c == "clear":
        os.system("cls" if os.name == "nt" else "clear")
        banner()
    elif c in ("exit", "quit"):
        _save_session()
        p("  <dim>Goodbye!</dim>")
        sys.exit(0)
    else:
        p(f"  <err>Unknown: /{c}</err>  <dim>Type /help</dim>")
        print()

def toolbar():
    ai = AGENTS[current_agent]
    return HTML(f"  {ai['emoji']} <b>{ai['label']}</b>  |  {provider}/{model}  |  <b>{BRAND}</b>")

def main():
    global current_agent
    os.system("cls" if os.name == "nt" else "clear")
    banner()

    global DISCOVERED_SKILLS
    DISCOVERED_SKILLS = discover_skills() + discover_skills_from_openpai()

    prev = _load_session()
    if prev:
        current_agent = prev.get("current_agent", current_agent)
        ts = prev.get("timestamp", "?")[:19]
        p(f"  <dim>Resuming session from {ts} | Agent: {AGENTS[current_agent]['label']}</dim>")
        print()

    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
        style=style,
    )

    while True:
        try:
            ai = AGENTS[current_agent]
            inp = session.prompt(
                HTML(f"<prompt>{ai['emoji']} {BRAND} > </prompt>"),
                bottom_toolbar=toolbar,
                style=style,
                completer=SlashCompleter(COMMANDS),
                complete_while_typing=True,
            )
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        inp = inp.strip()
        if not inp:
            continue

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
    p("\n  <dim>Goodbye!</dim>\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _save_session()
        p("\n  <dim>Goodbye!</dim>\n")
    except Exception as e:
        _save_session()
        p(f"\n  <err>Fatal: {e}</err>\n")
