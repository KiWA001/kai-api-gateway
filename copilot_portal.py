"""
Interactive Browser Portal for Copilot
--------------------------------------
Allows admin to interact with the browser directly through /qazmlp
"""

import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext

logger = logging.getLogger("kai_api.copilot_portal")

class CopilotPortal:
    """Manages an interactive browser session for Copilot."""
    
    def __init__(self):
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.is_initialized = False
        self.last_screenshot = "/tmp/copilot_portal.png"
        self.message_queue = []
        
    async def initialize(self):
        """Initialize the browser and navigate to Copilot."""
        if self.is_initialized:
            return
            
        try:
            logger.info("🚀 Portal: Launching browser...")
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Headless but we'll screenshot it
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            
            # Hide automation
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            self.page = await self.context.new_page()
            
            # Navigate to Copilot
            logger.info("Portal: Navigating to Copilot...")
            await self.page.goto("https://copilot.microsoft.com/", timeout=60000)
            await asyncio.sleep(5)
            
            self.is_initialized = True
            logger.info("✅ Portal: Browser ready!")
            
            # Take initial screenshot
            await self.take_screenshot()
            
        except Exception as e:
            logger.error(f"Failed to initialize portal: {e}")
            raise
    
    async def take_screenshot(self) -> str:
        """Take a screenshot of the current page state."""
        if not self.page:
            return ""
        try:
            await self.page.screenshot(path=self.last_screenshot, full_page=False)
            return self.last_screenshot
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""
    
    async def get_page_content(self) -> str:
        """Get current page HTML content for debugging."""
        if not self.page:
            return ""
        try:
            return await self.page.content()
        except:
            return ""
    
    async def send_message(self, message: str) -> str:
        """Send a message through the portal."""
        if not self.page:
            return "Error: Browser not initialized"
        
        try:
            # Find input field
            input_selectors = [
                'textarea',
                'div[contenteditable="true"]',
                '[data-testid="chat-input"]',
                '[role="textbox"]',
            ]
            
            input_found = False
            for selector in input_selectors:
                try:
                    el = await self.page.wait_for_selector(selector, timeout=5000)
                    if el:
                        # Click and type
                        await el.click()
                        await self.page.keyboard.type(message, delay=10)
                        await asyncio.sleep(0.5)
                        await self.page.keyboard.press("Enter")
                        input_found = True
                        logger.info(f"Portal: Message sent via {selector}")
                        break
                except:
                    continue
            
            if not input_found:
                return "Error: Could not find input field"
            
            # Wait for response
            await asyncio.sleep(3)
            
            # Try to extract response
            response_text = await self._extract_response()
            
            # Take screenshot after response
            await self.take_screenshot()
            
            return response_text or "No response yet, check screenshot"
            
        except Exception as e:
            logger.error(f"Portal send error: {e}")
            await self.take_screenshot()
            return f"Error: {str(e)}"
    
    async def _extract_response(self) -> str:
        """Try to extract the latest response."""
        try:
            return await self.page.evaluate("""
                () => {
                    const selectors = [
                        '[data-message-author-role="assistant"]',
                        '.message-content',
                        '.ac-textBlock',
                        '[class*="response"]',
                        'article',
                    ];
                    
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {
                            const last = els[els.length - 1];
                            const text = last.innerText || last.textContent || '';
                            if (text.trim().length > 10) return text.trim();
                        }
                    }
                    return '';
                }
            """)
        except:
            return ""
    
    async def click_new_chat(self):
        """Click the New Chat button."""
        if not self.page:
            return
        try:
            btn = await self.page.query_selector('button:has-text("New chat")')
            if btn:
                await btn.click()
                await asyncio.sleep(2)
                await self.take_screenshot()
        except Exception as e:
            logger.error(f"Click new chat error: {e}")
    
    async def refresh_page(self):
        """Refresh the page."""
        if not self.page:
            return
        try:
            await self.page.reload()
            await asyncio.sleep(5)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Refresh error: {e}")
    
    async def close(self):
        """Close the browser."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.is_initialized = False
            logger.info("Portal: Browser closed")
        except Exception as e:
            logger.error(f"Close error: {e}")

# Global portal instance
_portal: Optional[CopilotPortal] = None

def get_portal() -> CopilotPortal:
    """Get or create the global portal instance."""
    global _portal
    if _portal is None:
        _portal = CopilotPortal()
    return _portal
