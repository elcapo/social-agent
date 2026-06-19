from __future__ import annotations

from bs4 import BeautifulSoup


class PlaywrightBrowser:
    """Headless Chromium browser for JS-rendered pages.

    Lazily starts Playwright on the first ``fetch_page`` call.
    Use as a context manager or call ``close()`` explicitly.
    """

    def __init__(self) -> None:
        self._browser = None
        self._pw = None

    def __enter__(self) -> PlaywrightBrowser:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_page(self, url: str) -> tuple[BeautifulSoup, str]:
        if self._browser is None:
            self._start()

        page = self._browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            final_url = page.url
        finally:
            page.close()

        return BeautifulSoup(html, "html.parser"), final_url

    def close(self) -> None:
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

    def _start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for renderer='playwright'. "
                "Install it with: uv pip install playwright && python -m playwright install chromium"
            )

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(headless=True)
        except Exception:
            self._pw.stop()
            raise
