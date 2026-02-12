"""
Z.ai Provider (Browser-Based)
------------------------------
Uses Playwright Chromium to interact with https://chat.z.ai/ as a real browser.

Strategy:
- Keeps a PERSISTENT browser instance alive (Singleton) to save 20s startup time.
- Uses EPHEMERAL contexts (Tabs) per request for robust data isolation.
- Scrapes the AI response from the DOM.

Implementation:
- Async Playwright (Native integration with FastAPI)
- Lazy initialization of the browser
- Auto-recovery if browser crashes
"""

import asyncio
import logging
import time
import json
from providers.base import BaseProvider
from config import PROVIDER_MODELS

logger = logging.getLogger("kai_api.zai")

# Singleton Global State
_playwright = None
_browser = None
_lock = asyncio.Lock()

class ZaiProvider(BaseProvider):
    """AI provider using Z.ai via Persistent Playwright Browser."""

    # How long to wait for AI response in DOM (seconds)
    RESPONSE_TIMEOUT = 45
    # How long to wait after page load for JS hydration
    HYDRATION_DELAY = 2

    @property
    def name(self) -> str:
        return "zai"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("zai", [])

    @staticmethod
    def is_available() -> bool:
        """Check if Playwright is installed and usable."""
        try:
            from playwright.async_api import async_playwright
            return True
        except ImportError:
            return False

    async def _ensure_browser(self):
        """
        Start the persistent browser if it's not running.
        Thread-safe via asyncio Lock.
        """
        global _playwright, _browser
        
        async with _lock:
            if _browser and _browser.is_connected():
                return

            logger.info("🚀 Z.ai: Launching Persistent Browser...")
            from playwright.async_api import async_playwright
            
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",  # Saves RAM on server
                ],
            )
            logger.info("✅ Z.ai: Browser is Ready.")

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Send a message via Z.ai browser automation.
        
        Flow:
        1. Ensure Browser is running
        2. Create NEW Context (Ephemeral) -> Clean State
        3. Create Page
        4. Chat
        5. Close Context (Cleanup)
        """
        if not self.is_available():
            raise RuntimeError("Playwright not installed.")

        await self._ensure_browser()
        selected_model = model or "glm-5"
        
        # Create Ephemeral Context
        # This is where we get ISOLATION. Cookies/Storage are fresh.
        context = await _browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        
        # Hide webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        try:
            logger.info(f"Z.ai request: {selected_model}")
            
            # Step 1: Load Page (Fast navigation?)
            # Since context is new, we must load the site.
            await page.goto("https://chat.z.ai/", timeout=60000)
            
            # Smart waiting for textarea
            await page.wait_for_selector("textarea", timeout=60000)
            
            # Optional: Hydration wait (sometimes needed for event listeners)
            await asyncio.sleep(self.HYDRATION_DELAY)

            # Step 2: Type and Send
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"[System: {system_prompt}]\n\n{prompt}"

            await page.click("textarea")
            await page.keyboard.type(full_prompt, delay=10) # Slightly faster typing
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
            
            logger.info("Z.ai: Message sent, waiting for response...")

            # Step 3: Wait for response
            response_text = await self._wait_for_response(page)
            
            if not response_text:
                raise ValueError("Empty response from Z.ai")

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            logger.error(f"Z.ai Error: {e}")
            raise
        finally:
            # CRITICAL: Close the context to free memory and clear data
            await context.close()
            # We rarely close the browser itself, it stays up for the next request.

    async def _wait_for_response(self, page) -> str:
        """
        Async polling for response.
        """
        last_text = ""
        stable_count = 0
        required_stable = 3
        
        # Polling loop
        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)
            
            # Evaluate DOM
            current_text = await page.evaluate("""
                () => {
                    const selectors = [
                        '.prose',
                        '[data-message-role="assistant"]',
                        '.assistant-message',
                        '.message-content',
                        '.markdown-body',
                        '[class*="assistant"]',
                    ];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {
                            const last = els[els.length - 1];
                            const text = last.innerText || last.textContent || '';
                            if (text.trim().length > 0) return text.trim();
                        }
                    }
                    return '';
                }
            """)
            
            if not current_text:
                continue

            # Clean "Thinking..."
            clean = current_text
            for prefix in ["Thinking...\nSkip\n", "Thinking...\n"]:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]

            if clean == last_text and len(clean) > 0:
                stable_count += 1
                if stable_count >= required_stable:
                    return self._extract_final_answer(clean)
            else:
                stable_count = 0
                last_text = clean
                
            if i % 10 == 9:
                logger.info(f"Z.ai: Stream... {len(last_text)} chars")

        if last_text:
             logger.warning("Z.ai: Timeout, returning partial.")
             return self._extract_final_answer(last_text)
             
        raise TimeoutError("Z.ai no response")

    def _extract_final_answer(self, text: str) -> str:
        """Extract answer from thinking chain."""
        clean = text.strip()
        for prefix in ["Thinking...\nSkip\n", "Thinking...\n"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
                
        # Split by double newlines to find paragraphs
        parts = clean.split("\\n\\n")
        
        # If it looks like thinking process, skip the first part
        if "Thought Process" in clean[:50]:
             # Heuristic: The last big chunk is usually the answer
             pass
             
        # For now, return full clean text as Z.ai mostly outputs good markdown
        return clean

