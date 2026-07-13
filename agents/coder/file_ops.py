import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sandbox.file_access_policy import FileAccessPolicy
from sandbox.approval_gate import ApprovalGate, ApprovalRequest, ApprovalAction


class FileOps:
    def __init__(self):
        self.policy = FileAccessPolicy()
        self.gate = ApprovalGate()

    def read(self, path: str) -> str | None:
        resolved = os.path.abspath(path)
        if not self.policy.can_read(resolved):
            return None
        if not os.path.exists(resolved):
            return None
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def write(self, path: str, content: str) -> bool:
        resolved = os.path.abspath(path)
        if not self.policy.can_write(resolved):
            return False
        req = ApprovalRequest(
            action=ApprovalAction.FILE_WRITE,
            details=f"Write {len(content)} bytes to {resolved}",
            agent="coder",
            metadata={"path": resolved, "size": len(content)},
        )
        if not self.gate.request(req):
            return False
        try:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> bool:
        resolved = os.path.abspath(path)
        if not self.policy.can_delete(resolved):
            return False
        req = ApprovalRequest(
            action=ApprovalAction.FILE_DELETE,
            details=f"Delete file: {resolved}",
            agent="coder",
            metadata={"path": resolved},
        )
        if not self.gate.request(req):
            return False
        try:
            if os.path.isfile(resolved):
                os.remove(resolved)
                return True
            return False
        except Exception:
            return False

    def list_dir(self, path: str) -> list[str]:
        resolved = os.path.abspath(path)
        if not self.policy.can_read(resolved):
            return []
        if not os.path.isdir(resolved):
            return []
        try:
            return sorted(os.listdir(resolved))
        except Exception:
            return []
