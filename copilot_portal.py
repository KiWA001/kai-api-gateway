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
        self.last_activity = None
        
    def is_running(self) -> bool:
        """Check if the portal is currently running."""
        if not self.is_initialized:
            return False
        if not self.browser:
            return False
        try:
            # Check if browser is still connected
            return self.browser.is_connected()
        except:
            return False
        
    async def initialize(self):
        """Initialize the browser and navigate to Copilot with enhanced stealth."""
        if self.is_initialized:
            return
            
        try:
            logger.info("🚀 Portal: Launching browser with stealth...")
            self.playwright = await async_playwright().start()
            
            # Enhanced browser args for stealth
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=BlockInsecurePrivateNetworkRequests",
                    "--disable-features=InterestCohort",
                    "--window-size=1280,800",
                    "--start-maximized",
                    "--force-color-profile=srgb",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ],
            )
            
            # More realistic browser context
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                geolocation={"latitude": 40.7128, "longitude": -74.0060},  # NYC
                permissions=["geolocation"],
                color_scheme="light",
                reduced_motion="no-preference",
            )
            
            # Enhanced stealth script
            await self.context.add_init_script("""
                // Override navigator properties
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Add Chrome runtime
                window.chrome = {
                    runtime: {
                        OnInstalledReason: {
                            CHROME_UPDATE: "chrome_update",
                            INSTALL: "install",
                            SHARED_MODULE_UPDATE: "shared_module_update",
                            UPDATE: "update"
                        },
                        OnRestartRequiredReason: {
                            APP_UPDATE: "app_update",
                            OS_UPDATE: "os_update",
                            PERIODIC: "periodic"
                        },
                        PlatformArch: {
                            ARM: "arm",
                            ARM64: "arm64",
                            MIPS: "mips",
                            MIPS64: "mips64",
                            X86_32: "x86-32",
                            X86_64: "x86-64"
                        },
                        PlatformNaclArch: {
                            ARM: "arm",
                            MIPS: "mips",
                            MIPS64: "mips64",
                            MIPS64_EL: "mips64el",
                            ARM64: "arm64",
                            X86_32: "x86-32",
                            X86_64: "x86-64"
                        },
                        PlatformOs: {
                            ANDROID: "android",
                            CROS: "cros",
                            LINUX: "linux",
                            MAC: "mac",
                            OPENBSD: "openbsd",
                            WIN: "win"
                        },
                        RequestUpdateCheckStatus: {
                            NO_UPDATE: "no_update",
                            THROTTLED: "throttled",
                            UPDATE_AVAILABLE: "update_available"
                        }
                    }
                };
                
                // Override WebGL
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
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
    
    async def click_at_coordinates(self, x: float, y: float):
        """Click at specific coordinates on the page and immediately take screenshot."""
        if not self.page:
            logger.error("Portal: No page available for click")
            return
        
        try:
            logger.info(f"Portal: Clicking at coordinates ({x}, {y})")
            
            # First try clicking on main page
            await self.page.mouse.click(x, y)
            
            # Wait a short moment for the page to react
            await asyncio.sleep(0.5)
            
            # Check if there's an iframe at that location (CAPTCHA is often in iframe)
            iframe_clicked = await self._try_click_iframe(x, y)
            
            if iframe_clicked:
                logger.info("Portal: Clicked inside iframe")
            
            # Wait a bit more for any CAPTCHA processing
            await asyncio.sleep(1)
            
            # Take screenshot immediately
            await self.take_screenshot()
            logger.info("Portal: Click completed, screenshot taken")
            
        except Exception as e:
            logger.error(f"Portal click error: {e}")
            # Still try to take screenshot on error
            try:
                await self.take_screenshot()
            except:
                pass
    
    async def _try_click_iframe(self, x: float, y: float) -> bool:
        """Try to click inside iframes at the given coordinates."""
        try:
            # Get all iframes
            iframes = await self.page.query_selector_all('iframe')
            
            for iframe in iframes:
                try:
                    # Check if iframe is visible and contains the coordinates
                    box = await iframe.bounding_box()
                    if box and box['x'] <= x <= box['x'] + box['width'] and box['y'] <= y <= box['y'] + box['height']:
                        # Click inside the iframe
                        frame = await iframe.content_frame()
                        if frame:
                            # Calculate relative coordinates
                            rel_x = x - box['x']
                            rel_y = y - box['y']
                            await frame.mouse.click(rel_x, rel_y)
                            return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Iframe click error: {e}")
            return False
    
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
