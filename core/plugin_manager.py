"""Hot-loadable plugin system — drop .py files in plugins/ to add commands & agents."""
import os
import sys
import importlib.util
from pathlib import Path

class PluginRegistry:
    def __init__(self):
        self.commands = {}
        self.agents = {}
        self.tools = []

    def register_command(self, name: str, handler_fn, description: str = ""):
        self.commands[name] = {"handler": handler_fn, "description": description}

    def register_agent(self, name: str, agent_class, description: str = ""):
        self.agents[name] = {"class": agent_class, "description": description}

    def register_tool(self, fn):
        self.tools.append(fn)
        return fn


_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    return _registry


def discover_plugins(plugin_dir: str = None) -> list:
    if plugin_dir is None:
        plugin_dir = os.path.join(os.getcwd(), "plugins")
    plugins_dir = Path(plugin_dir)
    if not plugins_dir.is_dir():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return []

    loaded = []
    for py_file in sorted(plugins_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        name = py_file.stem
        try:
            spec = importlib.util.spec_from_file_location(f"plugins.{name}", py_file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f"plugins.{name}"] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(_registry)
                    loaded.append(name)
        except Exception as e:
            print(f"  [Plugin error] {name}: {e}")
    return loaded


def execute_command(name: str, args: str) -> str:
    cmd = _registry.commands.get(name)
    if cmd:
        return cmd["handler"](args)
    return None


def get_commands() -> dict:
    return {k: v["description"] for k, v in _registry.commands.items()}
