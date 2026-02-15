"""
Enhanced Browser Portal System
------------------------------
Full-featured browser with navigation controls, address bar, and advanced stealth.
Supports: Copilot, HuggingChat, ChatGPT, Gemini, Z.ai

Features:
- Back/Forward navigation
- Address bar for custom URLs
- Enhanced stealth (undetectable by Google)
- Reliable screenshot updates
- Better UI/UX
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
        requires_login=False,
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
    """Full-featured browser with navigation and enhanced stealth."""
    
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
        self.on_url_change_callback: Optional[Callable] = None
        self.on_title_change_callback: Optional[Callable] = None
        self.message_queue = []
        self.last_activity = None
        self.is_logged_in = False
        self._dom_change_task = None
        self._last_dom_hash = None
        self._auto_refresh_enabled = True
        self._last_url = None
        self._last_title = None
        self._navigation_history = []
        self._current_history_index = -1
        
    async def initialize(self, headless: bool = True, proxy: Optional[Any] = None):
        """Initialize the browser with maximum stealth."""
        if self.is_initialized:
            return
            
        try:
            logger.info(f"🚀 Portal [{self.provider.value}]: Launching stealth browser...")
            if proxy:
                logger.info(f"Using proxy: {proxy}")
            
            self.playwright = await async_playwright().start()
            
            # Maximum stealth args
            args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=site-isolation",
                "--disable-features=IsolateOrigins",
                f"--window-size={self.config.viewport['width']},{self.config.viewport['height']}",
                "--force-color-profile=srgb",
                "--disable-extensions-except=",
                "--disable-component-extensions-with-background-pages",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
                "--no-first-run",
                "--no-default-browser-check",
                "--password-store=basic",
                "--use-mock-keychain",
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
            
            # Use a real Chrome user agent
            self.context = await self.browser.new_context(
                viewport=self.config.viewport,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="light",
                geolocation={"latitude": 40.7128, "longitude": -74.0060},
                permissions=["geolocation"],
                java_script_enabled=True,
                has_touch=False,
                is_mobile=False,
                device_scale_factor=1,
            )
            
            # Maximum stealth scripts
            await self.context.add_init_script("""
                // Hide automation
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, '__proto__', {webdriver: undefined});
                
                // Fake plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: function() {
                        return [
                            {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "Portable Document Format"},
                            {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: ""},
                            {name: "Native Client", filename: "internal-nacl-plugin", description: ""},
                            {name: "Widevine Content Decryption Module", filename: "widevinecdmadapter.dll", description: "Widevine Content Decryption Module"}
                        ];
                    }
                });
                
                // Fake languages
                Object.defineProperty(navigator, 'languages', {
                    get: function() { return ['en-US', 'en']; }
                });
                
                // Fake Chrome
                window.chrome = {
                    runtime: {
                        OnInstalledReason: {CHROME_UPDATE: "chrome_update", INSTALL: "install", SHARED_MODULE_UPDATE: "shared_module_update", UPDATE: "update"},
                        OnRestartRequiredReason: {APP_UPDATE: "app_update", OS_UPDATE: "os_update", PERIODIC: "periodic"},
                        PlatformArch: {ARM: "arm", ARM64: "arm64", MIPS: "mips", MIPS64: "mips64", MIPS64EL: "mips64el", MIPSEL: "mipsel", X86_32: "x86-32", X86_64: "x86-64"},
                        PlatformNaclArch: {ARM: "arm", MIPS: "mips", MIPS64: "mips64", MIPS64EL: "mips64el", MIPSEL: "mipsel", MIPSEL64: "mipsel64", X86_32: "x86-32", X86_64: "x86-64"},
                        PlatformOs: {ANDROID: "android", CROS: "cros", LINUX: "linux", MAC: "mac", OPENBSD: "openbsd", WIN: "win"},
                        RequestUpdateCheckStatus: {NO_UPDATE: "no_update", THROTTLED: "throttled", UPDATE_AVAILABLE: "update_available"}
                    },
                    csi: function() {},
                    loadTimes: function() {}
                };
                
                // Fake notification permissions
                if (!window.Notification) {
                    window.Notification = {
                        permission: "default",
                        requestPermission: async function() { return "default"; }
                    };
                }
                
                // Override permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' 
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters)
                );
                
                // Hide Playwright/Automation
                delete navigator.__proto__.webdriver;
                
                // Canvas noise
                const getImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                    const imageData = getImageData.call(this, x, y, w, h);
                    const data = imageData.data;
                    for (let i = 0; i < data.length; i += 4) {
                        data[i] = data[i] + 1;
                    }
                    return imageData;
                };
                
                // WebGL noise
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.call(this, parameter);
                };
            """)
            
            self.page = await self.context.new_page()
            
            # Monitor navigation
            self.page.on("framenavigated", lambda frame: asyncio.create_task(self._on_navigation(frame)))
            self.page.on("title", lambda: asyncio.create_task(self._on_title_change()))
            
            # Navigate to initial URL
            logger.info(f"Portal [{self.provider.value}]: Navigating to {self.config.url}")
            await self.goto_url(self.config.url)
            
            # Handle login if required
            if self.config.requires_login and self.config.credentials:
                await self._perform_login()
            
            self.is_initialized = True
            logger.info(f"✅ Portal [{self.provider.value}]: Browser ready!")
            
            await self.take_screenshot()
            
        except Exception as e:
            logger.error(f"Failed to initialize portal [{self.provider.value}]: {e}")
            raise
    
    async def _on_navigation(self, frame):
        """Handle navigation events."""
        if frame == self.page.main_frame:
            url = frame.url
            if url != self._last_url:
                self._last_url = url
                logger.info(f"Portal [{self.provider.value}]: Navigated to {url}")
                if self.on_url_change_callback:
                    await self.on_url_change_callback(self.provider.value, url)
                await self.take_screenshot()
    
    async def _on_title_change(self):
        """Handle title change events."""
        try:
            title = await self.page.title()
            if title != self._last_title:
                self._last_title = title
                logger.info(f"Portal [{self.provider.value}]: Title changed to '{title}'")
                if self.on_title_change_callback:
                    await self.on_title_change_callback(self.provider.value, title)
        except:
            pass
    
    async def goto_url(self, url: str):
        """Navigate to a specific URL."""
        if not self.page:
            return False
        try:
            await self.page.goto(url, timeout=60000, wait_until="networkidle")
            self._last_url = url
            await asyncio.sleep(2)
            await self.take_screenshot()
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False
    
    async def go_back(self):
        """Go back in browser history."""
        if not self.page:
            return False
        try:
            await self.page.go_back(timeout=10000)
            await asyncio.sleep(1)
            await self.take_screenshot()
            return True
        except Exception as e:
            logger.warning(f"Go back failed: {e}")
            return False
    
    async def go_forward(self):
        """Go forward in browser history."""
        if not self.page:
            return False
        try:
            await self.page.go_forward(timeout=10000)
            await asyncio.sleep(1)
            await self.take_screenshot()
            return True
        except Exception as e:
            logger.warning(f"Go forward failed: {e}")
            return False
    
    async def get_current_url(self) -> str:
        """Get current page URL."""
        if not self.page:
            return ""
        try:
            return self.page.url
        except:
            return ""
    
    async def get_page_title(self) -> str:
        """Get current page title."""
        if not self.page:
            return ""
        try:
            return await self.page.title()
        except:
            return ""
    
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
    
    async def take_screenshot(self) -> str:
        """Take a screenshot."""
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
            await self.page.mouse.click(x, y)
            await asyncio.sleep(0.5)
            await self.take_screenshot()
        except Exception as e:
            logger.error(f"Click error: {e}")
    
    async def type_text(self, text: str):
        """Type text."""
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
    
    async def send_message(self, message: str):
        """Send a message."""
        if not self.page:
            return "Error: Browser not initialized"
        try:
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
            
            response = await self._extract_response()
            return response or "Message sent"
            
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


_portal_manager = PortalManager()

def get_portal_manager() -> PortalManager:
    """Get the global portal manager."""
    return _portal_manager
