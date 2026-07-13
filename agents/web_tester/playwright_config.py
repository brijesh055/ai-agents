import os

BROWSER_CONFIG = {
    "headless": True,
    "viewport": {"width": 1280, "height": 720},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Agents/1.0",
}

NAVIGATION_TIMEOUT = 30000

SCREENSHOT_DIR = os.path.join(os.getcwd(), ".ai_agents_output", "screenshots")
