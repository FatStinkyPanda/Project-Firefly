import logging

from playwright.async_api import async_playwright
import asyncio

logger = logging.getLogger("FireflyBrowserService")

class BrowserService:
    """
    Adapter for browser automation using Playwright.
    Supports navigation, clicking, typing, screenshots, and text extraction.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.browser = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Initializes the browser instance."""
        async with self._lock:
            if not self.browser:
                logger.info("Starting Chromium browser...")
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=True)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
                logger.info("Browser initialized successfully.")

    async def stop(self):
        """Closes the browser instance."""
        async with self._lock:
            if self.browser:
                logger.info("Closing browser...")
                await self.browser.close()
                await self.playwright.stop()
                self.browser = None
                self.context = None
                self.page = None
                logger.info("Browser closed.")

    async def navigate(self, url: str):
        """Navigates to a specific URL."""
        if not self.page: await self.start()
        logger.info(f"Navigating to: {url}")
        await self.page.goto(url, wait_until="networkidle")
        return {"status": "success", "url": self.page.url}

    async def click(self, selector: str):
        """Clicks an element specified by the selector."""
        if not self.page: await self.start()
        logger.info(f"Clicking: {selector}")
        await self.page.click(selector)
        return {"status": "success", "selector": selector}

    async def type(self, selector: str, text: str):
        """Types text into an element specified by the selector."""
        if not self.page: await self.start()
        logger.info(f"Typing '{text}' into: {selector}")
        await self.page.fill(selector, text)
        return {"status": "success", "selector": selector}

    async def screenshot(self, path: str = "screenshot.png"):
        """Captures a screenshot of the current page."""
        if not self.page: await self.start()
        logger.info(f"Taking screenshot to: {path}")
        await self.page.screenshot(path=path)
        return {"status": "success", "path": path}

    async def get_text(self):
        """Extracts text content from the current page."""
        if not self.page: await self.start()
        logger.info("Extracting page text.")
        text = await self.page.content() # or page.inner_text("body")
        # For AI consumption, inner_text is usually better
        text = await self.page.inner_text("body")
        return {"status": "success", "content": text[:5000]} # Truncate for now

    async def run_action(self, action: str, **kwargs):
        """Runs a browser action based on string name."""
        try:
            if action == "navigate":
                return await self.navigate(kwargs.get("url"))
            elif action == "click":
                return await self.click(kwargs.get("selector"))
            elif action == "type":
                return await self.type(kwargs.get("selector"), kwargs.get("text"))
            elif action == "screenshot":
                return await self.screenshot(kwargs.get("path", "screenshot.png"))
            elif action == "get_text":
                return await self.get_text()
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Browser action '{action}' failed: {e}")
            return {"status": "error", "message": str(e)}
