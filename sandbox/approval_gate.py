"""Human-in-the-loop — pauses for destructive ops."""
from dataclasses import dataclass
from enum import Enum
import json
import os


class ApprovalAction(Enum):
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    CODE_EXECUTE = "code_execute"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    NETWORK_REQUEST = "network_request"
    INSTALL_PACKAGE = "install_package"


@dataclass
class ApprovalRequest:
    action: ApprovalAction
    details: str
    agent: str
    metadata: dict = None


class ApprovalGate:
    def __init__(self, auto_approve: bool = False, mode: str = "interactive"):
        self._mode = mode
        self._auto_approve = auto_approve
        if auto_approve:
            self._mode = "auto"

    def request(self, req: ApprovalRequest) -> bool:
        if self._mode == "auto":
            return True
        if self._mode == "deny":
            return False
        if self._mode == "interactive":
            return self._ask_user(req)
        return False

    def set_mode(self, mode: str):
        if mode not in ("interactive", "auto", "deny"):
            raise ValueError(f"Invalid mode: {mode}. Must be one of: interactive, auto, deny")
        self._mode = mode

    def _ask_user(self, req: ApprovalRequest) -> bool:
        print(f"\n--- Approval Required ---")
        print(f"  Agent:    {req.agent}")
        print(f"  Action:   {req.action.value}")
        print(f"  Details:  {req.details}")
        if req.metadata:
            print(f"  Metadata: {json.dumps(req.metadata, indent=2)}")
        print("-------------------------")
        while True:
            response = input("Approve? (y/n): ").strip().lower()
            if response in ("y", "yes"):
                return True
            if response in ("n", "no"):
                return False
            print('Please enter "y" or "n".')
