"""
Microsoft Copilot Provider (Browser-Based with CAPTCHA Support)
---------------------------------------------------------------
Uses Playwright Chromium to interact with https://copilot.microsoft.com/ as a real browser.

Strategy:
- Uses persistent browser context with stored cookies
- Handles CAPTCHA by detecting it and returning special status
- Shows CAPTCHA challenge in admin dashboard (/qazmlp)
- Unlimited conversations (no 50 limit)
- Starts new chat for each request (no context sharing)
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any
from providers.base import BaseProvider
from config import PROVIDER_MODELS
from copilot_session import CopilotSessionManager

logger = logging.getLogger("kai_api.copilot")

_playwright = None
_browser = None
_lock = asyncio.Lock()

# Track if we're currently showing CAPTCHA
_captcha_pending = False
_captcha_context = None
_captcha_page = None


class CopilotProvider(BaseProvider):
    """AI provider using Microsoft Copilot via Persistent Playwright Browser."""

    RESPONSE_TIMEOUT = 90
    HYDRATION_DELAY = 3.0

    @property
    def name(self) -> str:
        return "copilot"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("copilot", ["copilot-gpt-4"])

    @staticmethod
    def is_available() -> bool:
        """Check if Playwright is installed and usable."""
        try:
            from playwright.async_api import async_playwright
            return True
        except ImportError:
            return False

    async def _ensure_browser(self):
        """Start the persistent browser if it's not running."""
        global _playwright, _browser

        async with _lock:
            if _browser and _browser.is_connected():
                return

            logger.info("🚀 Copilot: Launching Persistent Browser...")
            from playwright.async_api import async_playwright

            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            logger.info("✅ Copilot: Browser is Ready.")

    async def _check_and_handle_captcha(self, page) -> bool:
        """
        Check if CAPTCHA is present on the page.
        Returns True if CAPTCHA detected, False otherwise.
        """
        try:
            # Take a screenshot first for debugging
            await page.screenshot(path="/tmp/copilot_debug.png")
            
            # Check page content for CAPTCHA indicators
            page_content = await page.content()
            page_text = await page.evaluate("() => document.body.innerText || ''")
            
            # Check for various CAPTCHA indicators
            captcha_indicators = [
                "captcha",
                "verify you",
                "i'm not a robot",
                "security check",
                "challenge",
                "prove you're human",
                "human verification",
            ]
            
            content_lower = (page_content + page_text).lower()
            for indicator in captcha_indicators:
                if indicator in content_lower:
                    logger.warning(f"🤖 Copilot: CAPTCHA detected (indicator: '{indicator}')!")
                    return True
            
            # Also check for specific selectors
            captcha_selectors = [
                'iframe[src*="captcha"]', 
                'iframe[src*="challenge"]',
                '.captcha-container',
                '#challenge-form',
                '[class*="captcha"]',
                '[id*="captcha"]',
            ]
            
            for selector in captcha_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            logger.warning(f"🤖 Copilot: CAPTCHA detected (selector: '{selector}')!")
                            return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return False

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """Send a message via Copilot browser automation."""
        if not self.is_available():
            raise RuntimeError("Playwright not installed.")

        await self._ensure_browser()
        selected_model = model or "copilot-gpt-4"
        session_mgr = CopilotSessionManager()

        # Check if we have a valid session
        session_data = session_mgr.load_session()
        
        # Create context with cookies if we have them
        context = await _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Hide webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
        """)

        # Add cookies if we have them
        if session_data and session_data.get("cookies"):
            try:
                await context.add_cookies(session_data["cookies"])
                logger.info("✅ Copilot: Loaded existing session cookies")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

        page = await context.new_page()

        try:
            logger.info(f"Copilot request: {selected_model}")

            # Navigate to Copilot
            logger.info("Copilot: Navigating to copilot.microsoft.com...")
            await page.goto("https://copilot.microsoft.com/", timeout=60000)
            await asyncio.sleep(5)  # Wait longer for page to fully load
            
            # Take initial screenshot for debugging
            await page.screenshot(path="/tmp/copilot_initial.png")
            logger.info("Copilot: Initial screenshot saved")

            # Check for CAPTCHA
            has_captcha = await self._check_and_handle_captcha(page)
            
            if has_captcha:
                logger.warning("🤖 Copilot: CAPTCHA challenge detected!")
                
                # Save current state for CAPTCHA solving
                global _captcha_pending, _captcha_context, _captcha_page
                _captcha_pending = True
                _captcha_context = context
                _captcha_page = page
                
                # Take screenshot for admin dashboard
                screenshot_path = "/tmp/copilot_captcha.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"CAPTCHA screenshot saved to {screenshot_path}")
                
                raise Exception("CAPTCHA_REQUIRED")

            # Try to start a new chat (clear previous context)
            try:
                new_chat_btn = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
                if new_chat_btn:
                    await new_chat_btn.click()
                    await asyncio.sleep(2)
                    logger.info("Copilot: Started new chat")
            except:
                logger.info("Copilot: No 'New chat' button found, continuing...")

            # Find and use the chat input
            input_selectors = [
                '[data-testid="chat-input"]',
                'div[contenteditable="true"]',
                '[role="textbox"]',
                'textarea',
                '.input-area div[contenteditable]',
                '[placeholder*="Ask"]',
                '[placeholder*="Message"]',
            ]

            input_selector = None
            for sel in input_selectors:
                try:
                    el = await page.wait_for_selector(sel, timeout=5000)
                    if el:
                        input_selector = sel
                        logger.info(f"✅ Copilot: Found input selector: {sel}")
                        break
                except:
                    continue

            if not input_selector:
                # Save screenshot for debugging
                await page.screenshot(path="/tmp/copilot_no_input.png")
                raise RuntimeError("Could not find Copilot chat input")

            await asyncio.sleep(self.HYDRATION_DELAY)

            # Type the message
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"[System: {system_prompt}]\n\n{prompt}"

            await page.click(input_selector)
            await page.keyboard.type(full_prompt, delay=10)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")

            logger.info("Copilot: Message sent, waiting for response...")

            # Wait for response
            response_text = await self._wait_for_response(page)

            if not response_text:
                raise ValueError("Empty response from Copilot")

            # Save cookies after successful request
            try:
                cookies = await context.cookies()
                session_mgr.save_cookies(cookies)
                logger.info("✅ Copilot: Saved session cookies")
            except Exception as e:
                logger.warning(f"Failed to save cookies: {e}")

            # Close context
            await context.close()

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            if "CAPTCHA_REQUIRED" in str(e):
                raise
            # Save error screenshot
            try:
                await page.screenshot(path="/tmp/copilot_error.png")
            except:
                pass
            logger.error(f"Copilot Error: {e}")
            raise

    async def _wait_for_response(self, page) -> str:
        """Wait for and extract the AI response from the DOM."""
        last_text = ""
        stable_count = 0
        required_stable = 4

        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)

            # Extract response text
            current_text = await page.evaluate("""
                () => {
                    const selectors = [
                        '[data-testid="assistant-message"]',
                        '.message-content',
                        '[data-message-author-role="assistant"]',
                        '.ac-textBlock',
                        '[class*="response"]',
                        '[class*="message"] div',
                        '.markdown-body',
                        'article',
                        '[class*="conversation"] > div:last-child',
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

            if not current_text:
                continue

            # Clean the text
            clean = self._clean_response(current_text)

            if clean == last_text and len(clean) > 0:
                stable_count += 1
                if stable_count >= required_stable:
                    return clean
            else:
                stable_count = 0
                last_text = clean

            if i % 10 == 9:
                logger.info(f"Copilot: Stream... {len(last_text)} chars")

        if last_text:
            logger.warning("Copilot: Timeout, returning partial.")
            return last_text

        raise TimeoutError("Copilot no response")

    def _clean_response(self, text: str) -> str:
        """Clean up Copilot response text."""
        clean = text.strip()

        # Remove common UI artifacts
        clean = re.sub(r"^(Copilot\s*|Microsoft Copilot\s*)", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\n+\s*\n+", "\n\n", clean)

        return clean.strip()

    @staticmethod
    def is_captcha_pending() -> bool:
        """Check if there's a pending CAPTCHA challenge."""
        global _captcha_pending
        return _captcha_pending

    @staticmethod
    def get_captcha_context():
        """Get the browser context with pending CAPTCHA."""
        global _captcha_context
        return _captcha_context

    @staticmethod
    def get_captcha_page():
        """Get the page with pending CAPTCHA."""
        global _captcha_page
        return _captcha_page

    @staticmethod
    def clear_captcha_pending():
        """Clear the CAPTCHA pending state."""
        global _captcha_pending, _captcha_context, _captcha_page
        _captcha_pending = False
        _captcha_context = None
        _captcha_page = None
