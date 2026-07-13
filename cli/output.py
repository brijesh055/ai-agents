"""Live-streaming, colored, agent-name-prefixed output."""
import sys, time, threading
from datetime import datetime
from typing import Optional

class LiveOutput:
    """Handles real-time output from agents with prefixes and colors."""

    COLORS = {
        "researcher": "\033[36m",
        "web_tester": "\033[35m",
        "coder": "\033[33m",
        "reviewer": "\033[32m",
        "workflow": "\033[34m",
        "system": "\033[37m",
        "error": "\033[31m",
        "reset": "\033[0m",
    }

    SPINNER_CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        self.spinner_running = False
        self.spinner_thread: Optional[threading.Thread] = None
        self._spinner_message = ""

    def write(self, agent: str, message: str, level: str = "info"):
        """Write a line with agent prefix and color."""
        prefix = f"[{agent}]"
        color = self.COLORS.get(agent, self.COLORS["system"])
        reset = self.COLORS["reset"]
        timestamp = datetime.now().strftime("%H:%M:%S")

        if level == "error":
            color = self.COLORS["error"]

        line = f"{color}{timestamp} {prefix:15s}{reset} {message}"
        print(line, file=sys.stdout, flush=True)

    def start_spinner(self, message: str = "Working"):
        """Start a spinner animation in a background thread."""
        self._spinner_message = message
        self.spinner_running = True

        def _spin():
            idx = 0
            while self.spinner_running:
                char = self.SPINNER_CHARS[idx % len(self.SPINNER_CHARS)]
                print(f"\r{char} {self._spinner_message}...", end="", flush=True)
                idx += 1
                time.sleep(0.1)

        self.spinner_thread = threading.Thread(target=_spin, daemon=True)
        self.spinner_thread.start()

    def stop_spinner(self):
        """Stop the spinner and clear the line."""
        self.spinner_running = False
        if self.spinner_thread:
            self.spinner_thread.join(timeout=0.5)
        print("\r" + " " * 80 + "\r", end="", flush=True)

    def progress(self, current: int, total: int, message: str = ""):
        """Show a progress bar."""
        bar_len = 20
        filled = int(bar_len * current / total)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r{bar} {current}/{total} {message}", end="", flush=True)
        if current == total:
            print()

    def section(self, title: str):
        """Print a section header."""
        print(f"\n{'=' * 60}", file=sys.stdout, flush=True)
        print(f"  {title}", file=sys.stdout, flush=True)
        print(f"{'=' * 60}", file=sys.stdout, flush=True)
