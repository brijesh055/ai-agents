"""Main CLI entry point using Click."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import click
from workflows.registry import WorkflowRegistry
from agents.researcher.agent import ResearcherAgent
from agents.web_tester.agent import WebTestingAgent
from agents.coder.agent import CodingAgent
from agents.reviewer.agent import ReviewerAgent
from core.cost_tracker import CostTracker
from observability.metrics import MetricsCollector
from observability.dashboard.app import start_dashboard
from observability.logger import AgentLogger

@click.group()
def cli():
    """AI Agents — one-command multi-agent workflows."""

@cli.command()
@click.argument("workflow_name")
@click.option("--issue", "-i", default="", help="Issue URL or description")
@click.option("--repo", "-r", default=".", help="Repository path")
def run(workflow_name: str, issue: str, repo: str):
    """Run a pre-built workflow."""
    try:
        registry = WorkflowRegistry()
        registry.discover()
        result = registry.run(workflow_name, issue_url=issue, issue_description=issue, repo_path=repo)
        click.echo(click.style("\u2713 Complete!", fg="green"))
        click.echo(f"Cost: ${CostTracker().get_session_cost()}")
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--topic", "-t", required=True, help="Research topic")
def research(topic: str):
    """Run the five-lens researcher agent."""
    try:
        agent = ResearcherAgent()
        result = agent.research(topic)
        for lens, analysis in result.items():
            click.echo(click.style(f"\n=== {lens.upper()} ===", fg="blue", bold=True))
            preview = analysis[:500] + "..." if len(analysis) > 500 else analysis
            click.echo(preview)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.argument("url")
@click.option("--steps", "-s", default="", help="JSON array of test steps")
def test(url: str, steps: str):
    """Run web tests against a URL."""
    try:
        agent = WebTestingAgent()
        steps_list = json.loads(steps) if steps else [{"action": "navigate", "selector": url}]
        result = agent.run_test(url, steps_list)
        click.echo(json.dumps(result, indent=2))
    except json.JSONDecodeError:
        click.echo(click.style("Error: --steps must be valid JSON", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.argument("file_path")
@click.option("--instructions", "-i", required=True)
def code(file_path: str, instructions: str):
    """Modify code using AI."""
    try:
        agent = CodingAgent()
        result = agent.modify(file_path, instructions)
        click.echo(click.style("\u2713 Done", fg="green"))
        click.echo(result.get("summary", ""))
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.argument("file_path")
def review(file_path: str):
    """Review code for issues."""
    try:
        agent = ReviewerAgent()
        result = agent.review(file_path)
        for issue in result.get("issues", []):
            severity = issue["severity"]
            color = "red" if severity == "error" else "yellow" if severity == "warn" else "blue"
            line = issue.get("line", "?")
            click.echo(click.style(f"[{severity.upper()}] Line {line}: {issue['message']}", fg=color))
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
def status():
    """Show current session status and costs."""
    try:
        tracker = CostTracker()
        summary = tracker.summary()
        click.echo(click.style("=== Session Status ===", bold=True))
        click.echo(f"Calls: {summary['calls']}")
        click.echo(f"Tokens: {summary['tokens']['total']}")
        click.echo(f"Cost: ${summary['session_cost']}")
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--port", default=8080, help="Dashboard port")
def dashboard(port: int):
    """Start the observability dashboard."""
    try:
        start_dashboard(port=port)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
@click.option("--agent", default=None, help="Filter by agent")
def logs(agent: str):
    """View agent logs."""
    try:
        logger = AgentLogger()
        entries = logger.get_logs(agent=agent, limit=50)
        for entry in entries:
            ts = entry['timestamp'][:19]
            lvl = entry['level'].upper().ljust(5)
            ag = entry['agent'].ljust(15)
            click.echo(f"[{ts}] {lvl} {ag} {entry['message']}")
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

@cli.command()
def init():
    """Initialize AI Agents in the current directory."""
    try:
        from quickstart.init import init_project
        init_project()
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()
