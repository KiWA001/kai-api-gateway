"""
Unified Interactive Browser Portal System
-----------------------------------------
Manages interactive browser sessions for ALL browser-based providers.
Supports: Copilot, HuggingChat, ChatGPT, Gemini, Z.ai

Features:
- Full keyboard/mouse interaction through screenshot
- Multiple concurrent browser sessions
- Credential management for login-required sites
- Session persistence across page refreshes
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, Callable
from playwright.async_api import async_playwright, Page, BrowserContext
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("kai_api.browser_portal")


class PortalProvider(Enum):
    COPILOT = "copilot"
    HUGGINGCHAT = "huggingchat"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    ZAI = "zai"


@dataclass
class PortalCredentials:
    """Credentials for providers that require login."""
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None


@dataclass
class PortalConfig:
    """Configuration for each provider portal."""
    name: str
    url: str
    viewport: Dict[str, int]
    credentials: Optional[PortalCredentials] = None
    requires_login: bool = False


# Provider configurations
PORTAL_CONFIGS = {
    PortalProvider.COPILOT: PortalConfig(
        name="Microsoft Copilot",
        url="https://copilot.microsoft.com/",
        viewport={"width": 1280, "height": 800},
        requires_login=False,
    ),
    PortalProvider.HUGGINGCHAT: PortalConfig(
        name="HuggingChat",
        url="https://huggingface.co/chat",
        viewport={"width": 1280, "height": 800},
        credentials=PortalCredentials(
            username="one@bo5.store",
            password="Zzzzz1$."
        ),
        requires_login=True,
    ),
    PortalProvider.CHATGPT: PortalConfig(
        name="ChatGPT",
        url="https://chatgpt.com/",
        viewport={"width": 1280, "height": 800},
        requires_login=False,  # Can work without login initially
    ),
    PortalProvider.GEMINI: PortalConfig(
        name="Google Gemini",
        url="https://gemini.google.com/",
        viewport={"width": 1280, "height": 800},
        requires_login=False,
    ),
    PortalProvider.ZAI: PortalConfig(
        name="Z.ai Chat",
        url="https://chat.z.ai/",
        viewport={"width": 1280, "height": 800},
        requires_login=False,
    ),
}


class BrowserPortal:
    """Manages an interactive browser session."""
    
    def __init__(self, provider: PortalProvider, config: PortalConfig):
        self.provider = provider
        self.config = config
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.is_initialized = False
        self.screenshot_path = f"/tmp/portal_{provider.value}.png"
        self.on_screenshot_callback: Optional[Callable] = None
        self.message_queue = []
        self.last_activity = None
        self.is_logged_in = False
        
    async def initialize(self, headless: bool = True, proxy: Optional[Any] = None):
        """Initialize the browser with enhanced stealth and optional proxy."""
        if self.is_initialized:
            return
            
        try:
            logger.info(f"🚀 Portal [{self.provider.value}]: Launching browser...")
            if proxy:
                logger.info(f"Using proxy: {proxy}")
            
            self.playwright = await async_playwright().start()
            
            # Enhanced stealth args
            args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                f"--window-size={self.config.viewport['width']},{self.config.viewport['height']}",
                "--force-color-profile=srgb",
            ]
            
            # Build browser launch options
            launch_options = {
                "headless": headless,
                "args": args,
            }
            
            # Add proxy if provided
            if proxy:
                launch_options["proxy"] = proxy.to_playwright_format()
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            self.context = await self.browser.new_context(
                viewport=self.config.viewport,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="light",
            )
            
            # Enhanced stealth scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = { runtime: {} };
            """)
            
            self.page = await self.context.new_page()
            
            # Navigate to the site
            logger.info(f"Portal [{self.provider.value}]: Navigating to {self.config.url}")
            await self.page.goto(self.config.url, timeout=60000)
            await asyncio.sleep(3)
            
            # Handle login if required
            if self.config.requires_login and self.config.credentials:
                await self._perform_login()
            
            self.is_initialized = True
            logger.info(f"✅ Portal [{self.provider.value}]: Browser ready!")
            
            await self.take_screenshot()
            
        except Exception as e:
            logger.error(f"Failed to initialize portal [{self.provider.value}]: {e}")
            raise
    
    async def _perform_login(self):
        """Perform automatic login if credentials are provided."""
        if not self.config.credentials or not self.page:
            return
        
        creds = self.config.credentials
        
        try:
            logger.info(f"Portal [{self.provider.value}]: Attempting login...")
            
            # Wait for login form
            await self.page.wait_for_selector('input[type="email"], input[name="username"], input[type="text"]', timeout=10000)
            
            # Fill username
            username_selectors = ['input[type="email"]', 'input[name="username"]', 'input[type="text"]']
            for selector in username_selectors:
                try:
                    await self.page.fill(selector, creds.username)
                    break
                except:
                    continue
            
            # Fill password
            await self.page.fill('input[type="password"]', creds.password)
            
            # Click login
            await self.page.click('button[type="submit"], input[type="submit"]')
            
            # Wait for navigation
            await asyncio.sleep(5)
            
            self.is_logged_in = True
            logger.info(f"✅ Portal [{self.provider.value}]: Login successful")
            
        except Exception as e:
            logger.warning(f"Login failed for [{self.provider.value}]: {e}")
            # Continue anyway - user can login manually
    
    async def take_screenshot(self) -> str:
        """Take a screenshot and notify callback."""
        if not self.page:
            return ""
        try:
            await self.page.screenshot(path=self.screenshot_path, full_page=False)
            if self.on_screenshot_callback:
                await self.on_screenshot_callback(self.provider.value, self.screenshot_path)
            return self.screenshot_path
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""
    
    async def click(self, x: float, y: float):
        """Click at coordinates."""
        if not self.page:
            return
        try:
            # Try main page first
            await self.page.mouse.click(x, y)
            await asyncio.sleep(0.3)
            
            # Check for iframes
            await self._try_click_iframe(x, y)
            
            await asyncio.sleep(0.5)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Click error: {e}")
            await self.take_screenshot()
    
    async def _try_click_iframe(self, x: float, y: float):
        """Try clicking inside iframes."""
        try:
            iframes = await self.page.query_selector_all('iframe')
            for iframe in iframes:
                try:
                    box = await iframe.bounding_box()
                    if box and box['x'] <= x <= box['x'] + box['width']:
                        frame = await iframe.content_frame()
                        if frame:
                            rel_y = y - box['y']
                            await frame.mouse.click(x - box['x'], rel_y)
                            return True
                except:
                    continue
        except:
            pass
        return False
    
    async def type_text(self, text: str):
        """Type text at current cursor position."""
        if not self.page:
            return
        try:
            await self.page.keyboard.type(text, delay=10)
            await asyncio.sleep(0.3)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Type error: {e}")
    
    async def key_press(self, key: str):
        """Press a specific key."""
        if not self.page:
            return
        try:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.3)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Key press error: {e}")
    
    async def scroll(self, delta_x: int = 0, delta_y: int = 0):
        """Scroll the page."""
        if not self.page:
            return
        try:
            await self.page.mouse.wheel(delta_x, delta_y)
            await asyncio.sleep(0.3)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Scroll error: {e}")
    
    async def focus_input(self, x: float, y: float):
        """Focus an input field by clicking it."""
        if not self.page:
            return
        try:
            await self.page.mouse.click(x, y)
            await asyncio.sleep(0.2)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Focus error: {e}")
    
    async def send_message(self, message: str):
        """Send a message (type and press Enter)."""
        if not self.page:
            return "Error: Browser not initialized"
        try:
            # Find and click input
            input_selectors = [
                'textarea',
                'div[contenteditable="true"]',
                '[data-testid="chat-input"]',
                '[role="textbox"]',
                'input[type="text"]',
            ]
            
            for selector in input_selectors:
                try:
                    el = await self.page.wait_for_selector(selector, timeout=3000)
                    if el:
                        await el.click()
                        await self.page.keyboard.type(message, delay=10)
                        await asyncio.sleep(0.3)
                        await self.page.keyboard.press("Enter")
                        break
                except:
                    continue
            
            await asyncio.sleep(2)
            await self.take_screenshot()
            
            # Try to extract response
            response = await self._extract_response()
            return response or "Message sent - check screenshot"
            
        except Exception as e:
            await self.take_screenshot()
            return f"Error: {str(e)}"
    
    async def _extract_response(self) -> str:
        """Extract latest response."""
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
    
    async def new_chat(self):
        """Start a new chat."""
        if not self.page:
            return
        try:
            # Try to find New Chat button
            selectors = [
                'button:has-text("New chat")',
                'button:has-text("New Chat")',
                '[aria-label*="new chat" i]',
            ]
            for sel in selectors:
                try:
                    btn = await self.page.query_selector(sel)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        await self.take_screenshot()
                        return
                except:
                    continue
            
            # If no button, just refresh
            await self.refresh()
        except Exception as e:
            logger.error(f"New chat error: {e}")
    
    async def refresh(self):
        """Refresh the page."""
        if not self.page:
            return
        try:
            await self.page.reload()
            await asyncio.sleep(3)
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
            logger.info(f"Portal [{self.provider.value}]: Browser closed")
        except Exception as e:
            logger.error(f"Close error: {e}")
    
    def is_running(self) -> bool:
        """Check if portal is running."""
        if not self.is_initialized or not self.browser:
            return False
        try:
            return self.browser.is_connected()
        except:
            return False


# Portal manager
class PortalManager:
    """Manages multiple browser portals."""
    
    def __init__(self):
        self.portals: Dict[PortalProvider, BrowserPortal] = {}
    
    def get_portal(self, provider: PortalProvider) -> BrowserPortal:
        """Get or create a portal for a provider."""
        if provider not in self.portals:
            config = PORTAL_CONFIGS.get(provider)
            if not config:
                raise ValueError(f"Unknown provider: {provider}")
            self.portals[provider] = BrowserPortal(provider, config)
        return self.portals[provider]
    
    def get_active_portals(self) -> Dict[PortalProvider, BrowserPortal]:
        """Get all running portals."""
        return {k: v for k, v in self.portals.items() if v.is_running()}
    
    async def close_all(self):
        """Close all portals."""
        for portal in self.portals.values():
            await portal.close()


# Global instance
_portal_manager = PortalManager()

def get_portal_manager() -> PortalManager:
    """Get the global portal manager."""
    return _portal_manager
