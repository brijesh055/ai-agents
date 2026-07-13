"""Tests for agent handoff."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.handoff import AgentHandoff

def test_pass_and_receive():
    handoff = AgentHandoff()
    handoff.clear()
    
    handoff.pass_context("researcher", "coder", "Fix bug", {"bug": "null pointer"})
    received = handoff.receive_context("coder")
    assert len(received) == 1
    assert received[0]["from_agent"] == "researcher"
    assert received[0]["context"]["bug"] == "null pointer"
    print("[PASS] test_pass_and_receive passed")

def test_empty_inbox():
    handoff = AgentHandoff()
    handoff.clear()
    received = handoff.receive_context("nobody")
    assert received == []
    print("[PASS] test_empty_inbox passed")

def test_multiple_handoffs():
    handoff = AgentHandoff()
    handoff.clear()
    handoff.pass_context("a", "c", "task1", {"data": 1})
    handoff.pass_context("b", "c", "task2", {"data": 2})
    received = handoff.receive_context("c")
    assert len(received) == 2
    print("[PASS] test_multiple_handoffs passed")

if __name__ == "__main__":
    test_pass_and_receive()
    test_empty_inbox()
    test_multiple_handoffs()
    handoff = AgentHandoff()
    handoff.clear()
    print("\nAll handoff tests passed!")
