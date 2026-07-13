"""Initialize project — copies templates, creates .env, sets up dirs."""
import os, sys, shutil

def init_project(target_dir: str = "."):
    """Initialize a new AI Agents project in target_dir."""
    # Create directory structure
    dirs = [
        ".ai_agents_output/screenshots",
        ".ai_agents_output/reports",
        ".ai_agents_logs",
        ".ai_agents_state",
        ".ai_agents_handoffs",
        ".memory_data",
    ]
    for d in dirs:
        os.makedirs(os.path.join(target_dir, d), exist_ok=True)
    
    # Create .env if not exists
    env_path = os.path.join(target_dir, ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("""# AI Agents Configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
LLM_API_KEY=
LLM_BASE_URL=http://localhost:11434
""")
        print(f"[OK] Created {env_path}")
    
    # Create .gitkeep files
    for d in dirs:
        gitkeep = os.path.join(target_dir, d, ".gitkeep")
        if not os.path.exists(os.path.dirname(gitkeep)):
            os.makedirs(os.path.dirname(gitkeep), exist_ok=True)
    
    print("[OK] Project initialized!")
    print(f"  Run: python -m cli.main --help")
