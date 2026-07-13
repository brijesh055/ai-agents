"""Tests for cost tracker."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.cost_tracker import CostTracker

def test_log_call():
    tracker = CostTracker()
    tracker.log_call("test_agent", "gpt-4o", 100, 50)
    summary = tracker.summary()
    assert summary["calls"] == 1
    assert summary["tokens"]["input"] == 100
    assert summary["tokens"]["output"] == 50
    print("[PASS] test_log_call passed")

def test_session_cost():
    tracker = CostTracker()
    tracker.log_call("agent1", "gpt-4o", 1000000, 100000)  # ~$3.50
    assert tracker.get_session_cost() > 0
    assert tracker.get_agent_cost("agent1") > 0
    print("[PASS] test_session_cost passed")

def test_multiple_agents():
    tracker = CostTracker()
    tracker.log_call("agent_a", "gpt-4o", 1000, 500)
    tracker.log_call("agent_b", "gpt-4o", 2000, 1000)
    assert tracker.summary()["calls"] == 2
    print("[PASS] test_multiple_agents passed")

def test_reset():
    tracker = CostTracker()
    tracker.log_call("agent", "gpt-4o", 100, 50)
    tracker.reset()
    assert tracker.summary()["calls"] == 0
    print("[PASS] test_reset passed")

if __name__ == "__main__":
    test_log_call()
    test_session_cost()
    test_multiple_agents()
    test_reset()
    print("\nAll cost tracker tests passed!")
