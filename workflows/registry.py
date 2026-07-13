"""Discover & list available workflows."""
from typing import Callable, Any
import inspect
import os
import importlib
import importlib.util
import pkgutil
import sys

_workflow_registry: dict[str, dict] = {}


def workflow(name: str | None = None, description: str = ""):
    """Decorator that registers a function as a workflow.

    Usage:
        @workflow(name="bug-fix", description="Fix a bug end-to-end")
        def bug_fix_workflow(issue_url: str = "") -> dict: ...
    """
    def decorator(fn: Callable) -> Callable:
        wf_name = name or fn.__name__.replace("workflow_", "").replace("_", "-")
        wf_desc = description or fn.__doc__ or ""
        _workflow_registry[wf_name] = {
            "fn": fn,
            "name": wf_name,
            "description": wf_desc.strip(),
        }
        fn._is_workflow = True
        fn._workflow_name = wf_name
        fn._workflow_description = wf_desc.strip()
        return fn
    return decorator


class WorkflowRegistry:
    """Registry for discovering, registering, and running workflows."""

    def __init__(self):
        self._workflows: dict[str, dict] = {}

    # -- Public API -----------------------------------------------------------

    def register(self, name: str, description: str, workflow_fn: Callable):
        """Register a workflow by name."""
        if not callable(workflow_fn):
            raise TypeError(f"workflow_fn must be callable, got {type(workflow_fn)}")
        self._workflows[name] = {
            "fn": workflow_fn,
            "name": name,
            "description": description,
        }

    def get(self, name: str) -> Callable | None:
        """Get a workflow callable by name, or None."""
        entry = self._workflows.get(name)
        if entry is None:
            entry = _workflow_registry.get(name)
        return entry["fn"] if entry else None

    def list(self) -> list[dict]:
        """List all registered workflows with name and description."""
        seen: set[str] = set()
        results: list[dict] = []

        for entry in self._workflows.values():
            seen.add(entry["name"])
            results.append({"name": entry["name"], "description": entry["description"]})

        for entry in _workflow_registry.values():
            if entry["name"] not in seen:
                results.append({"name": entry["name"], "description": entry["description"]})

        return results

    def run(self, name: str, **kwargs: Any) -> Any:
        """Run a workflow by name with kwargs."""
        fn = self.get(name)
        if fn is None:
            raise KeyError(f"Unknown workflow: {name!r}. Available: {[e['name'] for e in self.list()]}")
        return fn(**kwargs)

    def discover(self):
        """Auto-discover workflows from the workflows module.

        Scans every .py file in the ``workflows`` package directory
        (except ``__init__.py`` and ``registry.py``) and imports them.
        Functions decorated with ``@workflow`` or whose name starts with
        ``workflow_``  are registered automatically.
        """
        pkg_name = __package__ or "workflows"
        pkg_path = os.path.dirname(__file__)

        # Ensure the package is importable
        if pkg_name not in sys.modules:
            spec = importlib.util.spec_from_file_location(pkg_name, os.path.join(pkg_path, "__init__.py"))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                sys.modules[pkg_name] = mod

        for importer, modname, ispkg in pkgutil.walk_packages(path=[pkg_path], prefix=f"{pkg_name}."):
            if modname == f"{pkg_name}.__init__" or modname == f"{pkg_name}.registry":
                continue
            try:
                importlib.import_module(modname)
            except Exception as exc:
                import warnings
                warnings.warn(f"Failed to import {modname}: {exc}")
                continue

        # Collect from decorator registry
        for wf_name, entry in _workflow_registry.items():
            if wf_name not in self._workflows:
                self._workflows[wf_name] = entry

        # Also pick up any workflow_ prefixed functions that weren't decorated
        for modname in list(sys.modules):
            if not modname.startswith(f"{pkg_name}."):
                continue
            mod = sys.modules[modname]
            for attr_name in dir(mod):
                if attr_name.startswith("workflow_") and not attr_name.startswith("__"):
                    obj = getattr(mod, attr_name)
                    if callable(obj) and not getattr(obj, "_is_workflow", False):
                        wf_name = attr_name.replace("workflow_", "").replace("_", "-")
                        if wf_name not in self._workflows:
                            desc = (obj.__doc__ or "").strip()
                            self._workflows[wf_name] = {
                                "fn": obj,
                                "name": wf_name,
                                "description": desc,
                            }
