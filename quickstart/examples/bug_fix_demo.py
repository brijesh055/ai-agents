"""Demo: Bug fix workflow on a sample file."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from workflows.bug_fix_workflow import bug_fix_workflow

def main():
    # Create a sample buggy file
    sample_code = """
def calculate_total(items):
    total == 0
    for i in items:
        total += i
    return total

def get_user(user_id):
    print(f"Fetching user {user_id}")
    api_key = "sk-1234567890abcdef"
    return {"id": user_id}
"""
    tmpdir = tempfile.mkdtemp()
    filepath = os.path.join(tmpdir, "buggy_code.py")
    with open(filepath, "w") as f:
        f.write(sample_code)
    
    result = bug_fix_workflow(issue_description="Fix bugs in buggy_code.py", repo_path=tmpdir)
    print("\nResults:", result.keys())
    print(f"Cost: ${result.get('cost', 0)}")

if __name__ == "__main__":
    main()
