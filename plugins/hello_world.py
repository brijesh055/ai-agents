"""Example plugin — adds /hello command and a custom agent."""

def register(registry):
    registry.register_command("hello", hello_handler, "Say hello with a custom message")
    registry.register_agent("hello_bot", HelloBotAgent, "Friendly hello bot")
    print("  [plugin] hello_world loaded")

def hello_handler(args: str) -> str:
    name = args.strip() or "World"
    return f"Hello, {name}! Brijesh'AI welcomes you."

class HelloBotAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def greet(self, name: str = "World") -> str:
        return f"Greetings, {name}! I am HelloBot from the plugin system."
