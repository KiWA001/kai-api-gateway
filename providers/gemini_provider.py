"""
Gemini Provider (Browser-Based)
------------------------------
Uses Playwright Chromium to interact with https://gemini.google.com/ as a real browser.

Strategy:
- Reuses the global Playwright browser instance if available (shared with Z.ai logic potentially, or standalone).
- Uses EPHEMERAL contexts (Tabs) per request for robust data isolation.
- Scrapes the AI response from the DOM.
- Appends "answer in plain text" to instructions.
"""

import asyncio
import logging
import re
import time
from providers.base import BaseProvider
from config import PROVIDER_MODELS

logger = logging.getLogger("kai_api.gemini")

# Reuse the global state/locking from zai_provider if possible, 
# but to avoid circular deps or complex refactors, we'll implement a similar singular pattern 
# or try to import if they were in a shared module. 
# For safety in this specific task, I will implement its own singleton management 
# or reuse the zai one if I can import it? 
# Actually, safest is to have its own manager or checks to see if browser is already running.
# However, playwight objects aren't easily shared across modules without a dedicated manager.
# I will implement a localized singleton for Gemini for now.

_playwright = None
_browser = None
_lock = asyncio.Lock()

class GeminiProvider(BaseProvider):
    """AI provider using Gemini via Persistent Playwright Browser."""

    RESPONSE_TIMEOUT = 60
    HYDRATION_DELAY = 2.0

    @property
    def name(self) -> str:
        return "gemini"

    def get_available_models(self) -> list[str]:
        return ["gemini-3-flash"]

    @staticmethod
    def is_available() -> bool:
        try:
            from playwright.async_api import async_playwright
            return True
        except ImportError:
            return False

    async def _ensure_browser(self):
        """
        Start the persistent browser if it's not running.
        """
        global _playwright, _browser
        
        async with _lock:
            if _browser and _browser.is_connected():
                return

            logger.info("🚀 Gemini: Launching Persistent Browser...")
            from playwright.async_api import async_playwright
            
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            logger.info("✅ Gemini: Browser is Ready.")

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        if not self.is_available():
            raise RuntimeError("Playwright not installed.")

        await self._ensure_browser()
        selected_model = model or "gemini-3-flash"
        
        # Create Ephemeral Context
        context = await _browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        try:
            logger.info(f"Gemini request: {selected_model}")
            
            # Step 1: Load Page
            await page.goto("https://gemini.google.com/", timeout=60000)
            
            # Selector strategies for Input
            # Verified via test script: div[contenteditable="true"] works
            input_selector = 'div[contenteditable="true"]'
            
            try:
                await page.wait_for_selector(input_selector, timeout=30000)
            except:
                # Fallback selectors
                input_selector = 'div[role="textbox"]'
                try:
                    await page.wait_for_selector(input_selector, timeout=5000)
                except:
                    input_selector = "rich-textarea"
                    await page.wait_for_selector(input_selector, timeout=5000)

            await asyncio.sleep(self.HYDRATION_DELAY)

            # Step 2: Type and Send
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"[System: {system_prompt}]\n\n{prompt}"
            
            # Append the plain text instruction as requested
            # User Change: Use 5 dots instead of newlines to prevent premature sending
            full_prompt += " ..... answer in plain text"

            await page.click(input_selector)
            await page.keyboard.type(full_prompt, delay=5)
            await asyncio.sleep(0.5)
            
            # Click Send button often reliable than Enter in rich text editors, 
            # but Enter usually works too. Let's try Enter first.
            await page.keyboard.press("Enter")
            
            logger.info("Gemini: Message sent...")

            # Step 3: Wait for response
            response_text = await self._wait_for_response(page)
            
            if not response_text:
                raise ValueError("Empty response from Gemini")

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            raise
        finally:
            await context.close()

    async def _wait_for_response(self, page) -> str:
        last_text = ""
        stable_count = 0
        required_stable = 3
        
        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)
            
            # Evaluate DOM
            # Gemini classes often look like 'model-response-text', 'message-content', etc.
            # We will use a generic strategy + specific known classes
            current_text = await page.evaluate("""
                () => {
                    const selectors = [
                        'model-response',
                        '.model-response-text',
                        '[data-message-author-role="model"]', 
                        '.message-content'
                    ];
                    
                    // Specific to Gemini: usually "model-response" tag or class
                    
                    let bestText = '';
                    
                    // Strategy: Find all potential response containers
                    // Return the last one that has text
                    
                    const candidates = document.querySelectorAll('model-response, [class*="model-response"]');
                    if (candidates.length > 0) {
                        const last = candidates[candidates.length - 1];
                        return last.innerText || last.textContent || '';
                    }
                    
                    return '';
                }
            """)
            
            if not current_text:
                continue

            clean = current_text.strip()
            
            if clean == last_text and len(clean) > 0:
                stable_count += 1
                if stable_count >= required_stable:
                    return clean
            else:
                stable_count = 0
                last_text = clean
                
            if i % 10 == 9:
                logger.info(f"Gemini: Stream... {len(last_text)} chars")

        if last_text:
             return last_text
             
        raise TimeoutError("Gemini no response")
