"""Tests for safety sandbox."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sandbox.code_sandbox import CodeSandbox

def test_run_python():
    sandbox = CodeSandbox()
    result = sandbox.run_python("print('hello')")
    assert result.success
    assert "hello" in result.stdout
    sandbox.cleanup()
    print("[PASS] test_run_python passed")

def test_run_python_error():
    sandbox = CodeSandbox()
    result = sandbox.run_python("1/0")
    assert not result.success
    assert "ZeroDivisionError" in result.stderr
    sandbox.cleanup()
    print("[PASS] test_run_python_error passed")

def test_timeout():
    sandbox = CodeSandbox()
    result = sandbox.run_python("import time; time.sleep(5)", timeout=1)
    assert result.timed_out
    sandbox.cleanup()
    print("[PASS] test_timeout passed")

if __name__ == "__main__":
    test_run_python()
    test_run_python_error()
    test_timeout()
    print("\nAll sandbox tests passed!")
