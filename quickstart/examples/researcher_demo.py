"""Demo: Run the researcher agent on a topic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agents.researcher.agent import ResearcherAgent

def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "Quantum computing in 2026"
    agent = ResearcherAgent()
    results = agent.research(topic)
    
    for lens, analysis in results.items():
        print(f"\n{'='*60}")
        print(f"  {lens.upper()}")
        print(f"{'='*60}")
        print(analysis[:1000])

if __name__ == "__main__":
    main()
