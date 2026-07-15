"""Provider-agnostic LLM caller using LiteLLM with cost tracking."""
import os
from litellm import completion
from .cost_tracker import CostTracker


def _load_env():
    """Load .env file from project root into environment."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()


class LLMClient:
    def __init__(self, provider: str = None, model: str = None, api_key: str = None, base_url: str = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "ollama")
        self.model = model or os.getenv("LLM_MODEL", "qwen2.5:7b")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.cost_tracker = CostTracker()

    def chat(self, messages: list[dict], temperature: float = 0.7, agent: str = "unknown") -> str:
        kwargs = {
            "model": f"{self.provider}/{self.model}" if self.provider != "openai" else self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.base_url:
            kwargs["api_base"] = self.base_url
        if self.api_key:
            kwargs["api_key"] = self.api_key

        response = completion(**kwargs)
        token_usage = response.get("usage", {})
        self.cost_tracker.log_call(
            agent=agent,
            model=self.model,
            tokens_in=token_usage.get("prompt_tokens", 0),
            tokens_out=token_usage.get("completion_tokens", 0),
        )
        return response["choices"][0]["message"]["content"]
