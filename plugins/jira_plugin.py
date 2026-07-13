"""Example: create/lookup tickets."""
from .plugin_base import Plugin, PluginContext
from typing import Any
import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse


class JiraPlugin(Plugin):
    @property
    def name(self) -> str:
        return "jira"

    def initialize(self, context: PluginContext):
        self.base_url = context.config.get("base_url") or os.getenv("JIRA_BASE_URL", "")
        self.email = context.config.get("email") or os.getenv("JIRA_EMAIL", "")
        self.api_token = context.config.get("api_token") or os.getenv("JIRA_API_TOKEN", "")
        self.project = context.config.get("project", "PROJ")

    def execute(self, action: str, params: dict) -> Any:
        if action == "create_ticket":
            return self._create_ticket(
                params.get("summary", ""),
                params.get("description", ""),
                params.get("issue_type", "Task"),
            )
        elif action == "find_ticket":
            return self._find_ticket(params.get("query", ""))
        raise ValueError(f"Unknown action: {action}")

    def _headers(self) -> dict:
        auth = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        }

    def _create_ticket(self, summary: str, description: str, issue_type: str) -> dict:
        base_url = self.base_url.rstrip("/")
        url = f"{base_url}/rest/api/3/issue"
        body = json.dumps({
            "fields": {
                "project": {"key": self.project},
                "summary": summary,
                "description": {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description}
                            ],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
            }
        }).encode()
        req = urllib.request.Request(
            url, data=body, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return {"success": True, "key": data.get("key"), "id": data.get("id")}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
        except urllib.error.URLError as e:
            return {"success": False, "error": str(e.reason)}

    def _find_ticket(self, query: str) -> dict:
        base_url = self.base_url.rstrip("/")
        jql = urllib.parse.quote(query)
        url = f"{base_url}/rest/api/3/search?jql={jql}&maxResults=10"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                issues = [
                    {
                        "key": i["key"],
                        "summary": i["fields"].get("summary", ""),
                        "status": i["fields"].get("status", {}).get("name", ""),
                    }
                    for i in data.get("issues", [])
                ]
                return {"success": True, "total": data.get("total", 0), "issues": issues}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
        except urllib.error.URLError as e:
            return {"success": False, "error": str(e.reason)}

    def shutdown(self):
        pass
