"""Which files agents can read/write — configurable."""
from pathlib import Path
from dataclasses import dataclass
import os


@dataclass
class AccessRule:
    path: str
    allow_read: bool = True
    allow_write: bool = False
    allow_delete: bool = False
    recursive: bool = True


class FileAccessPolicy:
    def __init__(self):
        self.rules: list[AccessRule] = []
        self._add_defaults()

    def _add_defaults(self):
        cwd = os.getcwd()
        self.rules.append(AccessRule(cwd, allow_read=True, allow_write=False, allow_delete=False, recursive=True))
        output_dir = os.path.join(cwd, ".ai_agents_output")
        self.rules.append(AccessRule(output_dir, allow_read=True, allow_write=True, allow_delete=False, recursive=True))
        system_paths = []
        if os.name == "nt":
            system_paths = [
                os.environ.get("SystemRoot", "C:\\Windows"),
                "C:\\Program Files",
                "C:\\Program Files (x86)",
                "C:\\ProgramData",
                "C:\\System Volume Information",
                "C:\\Windows.old",
            ]
            for p in ["Program Files", "Program Files (x86)", "ProgramData", "Windows", "System Volume Information"]:
                for d in [f"D:\\{p}", f"E:\\{p}"]:
                    system_paths.append(d)
        else:
            system_paths = ["/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64", "/opt", "/root", "/sys", "/proc",
                "/dev", "/boot"]
        for sp in system_paths:
            self.rules.append(AccessRule(sp, allow_read=False, allow_write=False, allow_delete=False, recursive=True))

    def add_rule(self, rule: AccessRule):
        rule.path = str(Path(rule.path).resolve())
        self.rules.append(rule)

    def _match(self, path: str) -> AccessRule | None:
        resolved = Path(path).resolve()
        best = None
        best_len = -1
        for rule in self.rules:
            rule_path = Path(rule.path).resolve()
            try:
                resolved.relative_to(rule_path)
            except ValueError:
                continue
            rule_len = len(str(rule_path))
            if rule_len > best_len:
                best = rule
                best_len = rule_len
        return best

    def can_read(self, path: str) -> bool:
        rule = self._match(path)
        return rule.allow_read if rule else False

    def can_write(self, path: str) -> bool:
        rule = self._match(path)
        return rule.allow_write if rule else False

    def can_delete(self, path: str) -> bool:
        rule = self._match(path)
        return rule.allow_delete if rule else False

    def grant(self, path: str, write: bool = False, delete: bool = False):
        resolved = str(Path(path).resolve())
        for rule in self.rules:
            if str(Path(rule.path).resolve()) == resolved:
                if write:
                    rule.allow_write = True
                if delete:
                    rule.allow_delete = True
                return
        self.rules.append(AccessRule(resolved, allow_read=True, allow_write=write, allow_delete=delete, recursive=True))

    def deny(self, path: str):
        resolved = str(Path(path).resolve())
        self.rules = [r for r in self.rules if str(Path(r.path).resolve()) != resolved]
        self.rules.append(AccessRule(resolved, allow_read=False, allow_write=False, allow_delete=False, recursive=True))
