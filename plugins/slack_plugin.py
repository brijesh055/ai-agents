"""Example: notify on task complete."""
from .plugin_base import Plugin, PluginContext
from typing import Any
import os
import json
import urllib.request
import urllib.error


class SlackPlugin(Plugin):
    @property
    def name(self) -> str:
        return "slack"

    def initialize(self, context: PluginContext):
        self.webhook_url = context.config.get("webhook_url") or os.getenv("SLACK_WEBHOOK_URL")
        self.channel = context.config.get("channel", "#ai-agents")

    def execute(self, action: str, params: dict) -> Any:
        if action == "notify":
            return self._send_message(params.get("message", ""))
        elif action == "send_file":
            return self._send_file(
                params.get("content", ""), params.get("filename", "report.txt")
            )
        raise ValueError(f"Unknown action: {action}")

    def _send_message(self, message: str) -> dict:
        if not self.webhook_url:
            return {"success": False, "error": "No webhook URL configured"}
        payload = json.dumps({"text": message, "channel": self.channel}).encode()
        req = urllib.request.Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return {"success": True}
        except urllib.error.URLError as e:
            return {"success": False, "error": str(e)}

    def _send_file(self, content: str, filename: str) -> dict:
        message = f"*File:* {filename}\n```\n{content[:3000]}\n```"
        return self._send_message(message)

    def shutdown(self):
        pass
