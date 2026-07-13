"""Demo: PR review on a local diff."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from workflows.pr_review_workflow import pr_review_workflow

def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    result = pr_review_workflow(repo_path=repo)
    print("\n=== Review Results ===")
    for issue in result.get("issues", []):
        print(f"[{issue['severity'].upper()}] {issue['message']}")

if __name__ == "__main__":
    main()
