"""Default workflow that showcases the system — runs researcher then coder then reviewer."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.researcher.agent import ResearcherAgent
from agents.coder.agent import CodingAgent
from agents.reviewer.agent import ReviewerAgent
from core.handoff import AgentHandoff
from core.cost_tracker import CostTracker
from observability.logger import AgentLogger
from cli.output import LiveOutput

def demo_workflow(topic: str):
    """
    End-to-end demo: Research a topic → Generate code → Review the output.
    This showcases the full system in under 30 seconds.
    """
    output = LiveOutput()
    logger = AgentLogger(agent_name="demo")
    handoff = AgentHandoff()
    tracker = CostTracker()
    
    output.section(f"AI Agents Demo: {topic}")
    
    # Step 1: Research
    output.write("system", "Starting research...")
    researcher = ResearcherAgent()
    research = researcher.research(topic)
    output.write("researcher", f"Completed {len(research)} lenses of analysis")
    
    # Step 2: Handoff
    handoff.pass_context("researcher", "coder", f"Generate code for: {topic}", research)
    output.write("system", "Passing context to coding agent...")
    
    # Step 3: Coder
    output.write("coder", "Generating code...")
    coder = CodingAgent()
    result = coder.generate(f"Create a Python script based on: {topic}")
    output.write("coder", f"Generated code for {topic}")
    
    # Step 4: Reviewer
    output.write("reviewer", "Reviewing generated code...")
    reviewer = ReviewerAgent()
    review = reviewer.review("generated_code.py", result.get("code", ""))
    output.write("reviewer", f"Found {len(review.get('issues', []))} issues")
    
    # Summary
    cost = tracker.get_session_cost()
    output.section("Complete!")
    output.write("system", f"Total cost: ${cost}")
    output.write("system", f"Research lenses: {len(research)}")
    output.write("system", f"Issues found: {len(review.get('issues', []))}")
    
    return {
        "research": research,
        "code": result,
        "review": review,
        "cost": cost,
    }

if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "a Python CLI calculator with tests"
    demo_workflow(topic)
