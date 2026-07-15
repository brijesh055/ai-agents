"""Tool-calling loop: agent requests tools → system executes → agent continues."""
import json
import re
from core.llm_client import LLMClient
from core.tools import get_tool_schemas, execute_tool

TOOL_CALL_RE = re.compile(r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^}]+\})\s*\}', re.DOTALL)

class ToolRunner:
    def __init__(self, llm=None, max_turns: int = 15):
        self.llm = llm or LLMClient()
        self.max_turns = max_turns

    def run(self, system_prompt: str, user_message: str, agent: str = "tool_user") -> str:
        schemas = get_tool_schemas()
        tools_desc = "\n".join(
            f"- {s['name']}({', '.join(s['parameters'].get('properties', {}).keys())}): {s['description']}"
            for s in schemas
        )
        sys_prompt = (
            system_prompt + "\n\n"
            "You have access to tools. When you need to use a tool, output JSON on its own line like this:\n"
            '{"tool": "tool_name", "args": {"param": "value"}}\n'
            "After the tool result, continue your reasoning. When done, output your final answer.\n\n"
            f"Available tools:\n{tools_desc}"
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_message},
        ]

        for turn in range(self.max_turns):
            response = self.llm.chat(messages, agent=agent)
            match = TOOL_CALL_RE.search(response)
            if not match:
                return response
            tool_name = match.group(1)
            try:
                tool_args = json.loads(match.group(2))
            except json.JSONDecodeError:
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": "Invalid tool call JSON. Use valid JSON."})
                continue
            result = execute_tool(tool_name, tool_args)
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Tool {tool_name} result:\n{result[:3000]}\n\nContinue based on this result."})

        return "Max turns reached. Final answer:\n" + response
