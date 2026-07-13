import sys
import os
import json
import traceback
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.llm_client import LLMClient
from core.memory_store import MemoryStore
from core.safety_sandbox import SafetySandbox
from agents.web_tester.playwright_config import BROWSER_CONFIG, NAVIGATION_TIMEOUT, SCREENSHOT_DIR


class WebTestResult:
    def __init__(self, url, success, screenshot_path=None, page_content=None, errors=None):
        self.url = url
        self.success = success
        self.screenshot_path = screenshot_path
        self.page_content = page_content
        self.errors = errors or []

    def to_dict(self):
        return {
            "url": self.url,
            "success": self.success,
            "screenshot_path": self.screenshot_path,
            "errors": self.errors,
        }


class WebTestingAgent:
    def __init__(self, llm=None, memory=None, headless=None):
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryStore()
        self.headless = headless if headless is not None else BROWSER_CONFIG.get("headless", True)
        self._playwright = None
        self._browser = None
        self._page = None
        self._ensure_screenshot_dir()

    def _ensure_screenshot_dir(self):
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    def _ensure_browser(self):
        if self._browser is not None:
            return
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        launch_kwargs = {
            "headless": self.headless,
        }
        if "viewport" in BROWSER_CONFIG:
            vp = BROWSER_CONFIG["viewport"]
            launch_kwargs["args"] = [f"--window-size={vp['width']},{vp['height']}"]
        self._browser = self._playwright.chromium.launch(**launch_kwargs)
        context = self._browser.new_context(
            viewport=BROWSER_CONFIG.get("viewport"),
            user_agent=BROWSER_CONFIG.get("user_agent"),
        )
        self._page = context.new_page()

    def navigate(self, url: str) -> WebTestResult:
        try:
            self._ensure_browser()
            self._page.goto(url, timeout=NAVIGATION_TIMEOUT, wait_until="domcontentloaded")
            return WebTestResult(
                url=url,
                success=True,
                page_content=self._page.content(),
            )
        except Exception as e:
            return WebTestResult(
                url=url,
                success=False,
                errors=[f"Navigation failed: {traceback.format_exc()}"],
            )

    def click(self, selector: str) -> WebTestResult:
        try:
            self._ensure_browser()
            self._page.wait_for_selector(selector, timeout=NAVIGATION_TIMEOUT)
            self._page.click(selector)
            return WebTestResult(
                url=self._page.url,
                success=True,
                page_content=self._page.content(),
            )
        except Exception as e:
            return WebTestResult(
                url=self._page.url if self._page else "",
                success=False,
                errors=[f"Click failed on '{selector}': {traceback.format_exc()}"],
            )

    def fill(self, selector: str, value: str) -> WebTestResult:
        try:
            self._ensure_browser()
            self._page.wait_for_selector(selector, timeout=NAVIGATION_TIMEOUT)
            self._page.fill(selector, value)
            return WebTestResult(
                url=self._page.url,
                success=True,
            )
        except Exception as e:
            return WebTestResult(
                url=self._page.url if self._page else "",
                success=False,
                errors=[f"Fill failed on '{selector}': {traceback.format_exc()}"],
            )

    def screenshot(self, path: str = None) -> str:
        try:
            self._ensure_browser()
            if path is None:
                fname = f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.png"
                path = os.path.join(SCREENSHOT_DIR, fname)
            self._page.screenshot(path=path, full_page=True)
            return path
        except Exception as e:
            return None

    def extract_text(self, selector: str = "body") -> str:
        try:
            self._ensure_browser()
            element = self._page.query_selector(selector)
            if element:
                return element.inner_text()
            return ""
        except Exception as e:
            return ""

    def run_test(self, url: str, steps: list[dict]) -> dict:
        results = []
        nav_result = self.navigate(url)
        results.append({"step": 0, "action": "navigate", "url": url, "result": nav_result.to_dict()})
        if not nav_result.success:
            return {"url": url, "steps": results, "passed": False, "error": "Initial navigation failed"}

        for i, step in enumerate(steps, 1):
            action = step.get("action")
            selector = step.get("selector")
            value = step.get("value")

            if action == "click":
                result = self.click(selector)
            elif action == "fill":
                result = self.fill(selector, value)
            elif action == "screenshot":
                spath = self.screenshot(step.get("path"))
                result = WebTestResult(url=self._page.url if self._page else "", success=bool(spath),
                    screenshot_path=spath)
            elif action == "assert":
                expected = step.get("expected", "")
                actual = self.extract_text(selector)
                passed = expected.lower() in actual.lower() if expected else True
                result = WebTestResult(url=self._page.url if self._page else "", success=passed)
                if not passed:
                    result.errors.append(f"Expected '{expected}' not found in '{selector}'")
            else:
                result = WebTestResult(url=self._page.url if self._page else "", success=False,
                    errors=[f"Unknown action: {action}"])

            results.append({"step": i, "action": action, "selector": selector, "result": result.to_dict()})

        passed = all(r["result"]["success"] for r in results)
        test_result = {"url": url, "steps": results, "passed": passed}
        self.memory.store("web_tester", f"test:{url}", test_result)
        return test_result

    def close(self):
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __del__(self):
        self.close()
