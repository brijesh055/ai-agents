"""Abstract base class for plugins."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PluginContext:
    agent_name: str
    task_id: str
    config: dict


class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def initialize(self, context: PluginContext): ...

    @abstractmethod
    def execute(self, action: str, params: dict) -> Any: ...

    @abstractmethod
    def shutdown(self): ...


class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list(self) -> list[str]:
        return list(self._plugins.keys())

    def execute(self, plugin_name: str, action: str, params: dict) -> Any:
        plugin = self.get(plugin_name)
        if plugin is None:
            raise ValueError(f"Plugin '{plugin_name}' not registered")
        return plugin.execute(action, params)
