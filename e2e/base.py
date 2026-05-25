"""Base class for Playwright end-to-end tests.

Tests run against a real Django dev server (StaticLiveServerTestCase) using
a headless Chromium browser. Each test gets a fresh browser context so cookies
and storage don't leak across tests.

Screenshots are written to ``screenshots/<TestClass>/<test_name>/NN_label.png``
so they're easy to flip through in order after a run.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

# Playwright's sync API runs an asyncio loop in a worker thread, which makes
# Django think it's in an async context during test teardown (DB flush).
# Opt out of that safety check for the e2e suite — we're never crossing
# threads with a single connection.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from django.contrib.staticfiles.testing import StaticLiveServerTestCase  # noqa: E402
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright  # noqa: E402

SCREENSHOT_ROOT = Path(__file__).resolve().parent.parent / "screenshots"

# Default phone-ish viewport so screenshots reflect the mobile-first design.
DEFAULT_VIEWPORT = {"width": 414, "height": 896}


class PlaywrightTestCase(StaticLiveServerTestCase):
    """Shared Playwright setup. Subclass and write test_* methods."""

    browser: Browser

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._playwright = sync_playwright().start()
        cls.browser = cls._playwright.chromium.launch(headless=True)
        cls._screenshot_dir = SCREENSHOT_ROOT / cls.__name__
        if cls._screenshot_dir.exists():
            shutil.rmtree(cls._screenshot_dir)
        cls._screenshot_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._playwright.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.context: BrowserContext = self.browser.new_context(
            viewport=DEFAULT_VIEWPORT,
            device_scale_factor=2,
        )
        self.page: Page = self.context.new_page()
        self._shot_dir = self._screenshot_dir / self._testMethodName
        self._shot_dir.mkdir(parents=True, exist_ok=True)
        self._shot_counter = 0

    def tearDown(self):
        self.context.close()
        super().tearDown()

    # --- helpers ---

    def url(self, path: str) -> str:
        return self.live_server_url + path

    def shot(self, label: str) -> Path:
        """Save a full-page screenshot tagged with an incrementing index."""
        self._shot_counter += 1
        path = self._shot_dir / f"{self._shot_counter:02d}_{label}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def login_parent(self, username: str, password: str) -> None:
        self.page.goto(self.url("/login/parent/"))
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_url(lambda u: "/login/" not in u)

    def login_kid(self, kid_id: int, pin: str) -> None:
        self.page.goto(self.url(f"/login/kid/{kid_id}/"))
        self.page.fill('input[name="pin"]', pin)
        self.page.click('button[type="submit"]')
        self.page.wait_for_url(lambda u: "/login/" not in u)

    def switch_user(self) -> None:
        self.page.click('a:has-text("Switch user")')
        self.page.wait_for_url(lambda u: "/login/" in u)
