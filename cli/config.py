"""Init wizard that sets up .env + checks deps."""
import os, sys, subprocess


def check_dependencies() -> list[str]:
    """Check if required tools are installed."""
    missing = []
    if sys.version_info < (3, 10):
        missing.append("Python 3.10+")
    try:
        import playwright
    except ImportError:
        missing.append("playwright (pip install playwright)")
    try:
        import litellm
    except ImportError:
        missing.append("litellm (pip install litellm)")
    return missing


def create_env_file(env_path: str = ".env"):
    """Create .env file with user-provided values."""
    if os.path.exists(env_path):
        try:
            overwrite = input(".env already exists. Overwrite? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if overwrite != "y":
            print("Keeping existing .env")
            return

    print("\n=== AI Agents Configuration ===")
    print("(Press Enter for defaults — local Ollama is recommended)\n")

    try:
        provider = input("LLM Provider [ollama]: ").strip() or "ollama"
        model_default = "qwen2.5:7b" if provider == "ollama" else "gpt-4o"
        model = input(f"Model [{model_default}]: ").strip() or model_default

        api_key = ""
        base_url = ""

        if provider != "ollama":
            api_key = input("API Key: ").strip()
            while not api_key:
                print("API Key is required for cloud providers.")
                api_key = input("API Key: ").strip()

        if provider == "ollama":
            base_url = (
                input("Ollama URL [http://localhost:11434]: ").strip()
                or "http://localhost:11434"
            )
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return

    content = f"""# LLM Provider (local-first — Ollama works out of the box)
LLM_PROVIDER={provider}
LLM_MODEL={model}
LLM_API_KEY={api_key or ''}
LLM_BASE_URL={base_url or ''}
"""
    try:
        with open(env_path, "w") as f:
            f.write(content)
        print(f"\n\u2713 Created {env_path}")
    except OSError as e:
        print(f"Error writing {env_path}: {e}")
        return

    if provider == "ollama":
        print("\nTip: Make sure Ollama is running:")
        print("  ollama pull " + model)
        print("  ollama serve")


def init_project():
    """Full initialization: deps check, .env setup, dirs."""
    print("=== AI Agents Initialization ===\n")

    missing = check_dependencies()
    if missing:
        print("Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        try:
            install = input("\nInstall missing pip packages? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if install == "y":
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "litellm", "playwright", "click"]
                )
                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", "chromium"]
                )
                print("\u2713 Dependencies installed")
            except subprocess.CalledProcessError as e:
                print(f"Error installing dependencies: {e}")
                return
    else:
        print("\u2713 All dependencies found")

    create_env_file()

    try:
        os.makedirs(".ai_agents_output", exist_ok=True)
        os.makedirs(".ai_agents_logs", exist_ok=True)
    except OSError as e:
        print(f"Error creating directories: {e}")
        return

    print("\n\u2713 AI Agents initialized!")
    print("   Run: python -m cli.main --help")
