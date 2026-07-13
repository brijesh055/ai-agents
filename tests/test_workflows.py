"""Tests for workflows."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workflows.registry import WorkflowRegistry

def test_registry_register():
    registry = WorkflowRegistry()
    
    def dummy_workflow():
        return "done"
    
    registry.register("test_wf", "A test workflow", dummy_workflow)
    listed = registry.list()
    assert any(w["name"] == "test_wf" for w in listed)
    print("[PASS] test_registry_register passed")

def test_registry_get():
    registry = WorkflowRegistry()
    
    def dummy():
        return "done"
    
    registry.register("get_test", "Get test", dummy)
    fn = registry.get("get_test")
    assert fn is not None
    assert fn() == "done"
    print("[PASS] test_registry_get passed")

def test_registry_run():
    registry = WorkflowRegistry()
    
    def dummy(**kwargs):
        return {"status": "ok", "input": kwargs}
    
    registry.register("run_test", "Run test", dummy)
    result = registry.run("run_test", foo="bar")
    assert result["status"] == "ok"
    assert result["input"]["foo"] == "bar"
    print("[PASS] test_registry_run passed")

if __name__ == "__main__":
    test_registry_register()
    test_registry_get()
    test_registry_run()
    print("\nAll workflow tests passed!")
