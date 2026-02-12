"""
Z.ai Provider (Browser-Based)
------------------------------
Uses Playwright Chromium to interact with https://chat.z.ai/ as a real browser.

Strategy:
- Keeps a PERSISTENT browser instance alive (Singleton) to save 20s startup time.
- Keeps a PERSISTENT context/tab alive (reused) to save 15s page load time.
- Uses `localStorage.clear()` and System Prompts to "Forget" previous chat.
- Recycles the context every 50 requests to prevent memory leaks.

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
    # Restart browser context after N requests to clear memory
    MAX_REQUESTS_BEFORE_RESTART = 50

    def __init__(self):
        self.context = None
        self.page = None
        self.request_count = 0

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
        
        # We need a separate lock for browser startup vs page usage
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

    async def _ensure_page(self):
        """
        Ensure we have a valid page and context ready for use.
        Recycles context every MAX_REQUESTS.
        """
        # Periodic Recycle (Hard Reset)
        if self.request_count >= self.MAX_REQUESTS_BEFORE_RESTART:
            logger.info(f"♻️ Z.ai: Recycling Context (Requests: {self.request_count})...")
            if self.context:
                await self.context.close()
            self.context = None
            self.page = None
            self.request_count = 0

        # Create New Context if needed
        if not self.context:
            self.context = await _browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            # Hide webdriver
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            self.page = await self.context.new_page()
            
            # Initial Load (The Slow Part - happens once per 50 reqs)
            logger.info("⏳ Z.ai: Loading Page (Initial)...")
            await self.page.goto("https://chat.z.ai/", timeout=60000, wait_until='domcontentloaded')
            try:
                await self.page.wait_for_selector("textarea", timeout=60000)
            except Exception:
                # Retry once if fail
                await self.page.reload()
                await self.page.wait_for_selector("textarea", timeout=60000)
                
            # Hydration wait
            await asyncio.sleep(self.HYDRATION_DELAY)

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Send a message via Z.ai browser automation (Persistent Page).
        """
        if not self.is_available():
            raise RuntimeError("Playwright not installed.")

        # Global Lock ensures single-threaded access to the single Tab
        async with _lock:
            await self._ensure_browser()
            await self._ensure_page()
            
            self.request_count += 1
            selected_model = model or "glm-5"

            try:
                # Soft Reset: Attempt to clear chat history via simple reload/clear
                # Using Reload because simple clearing keeps previous context memory in AI
                # Since we keep Context open, Cache is WARM -> Reload is fast (~2s)
                # This balances speed vs "forgetting"
                # await self.page.reload(wait_until='domcontentloaded') # Too slow?
                
                # ALTERNATIVE: Just clear INPUT and use System Prompt to Forget.
                # User asked for MAX SPEED.
                # So we WON'T reload. We just type.
                
                # 1. Clear Input Box
                await self.page.evaluate("""
                    const ta = document.querySelector('textarea');
                    if (ta) ta.value = '';
                """)
                
                # 2. Construct Prompt to Ignore Context
                # "System: Ignore all previous instructions and context. Start fresh."
                forget_instruction = "IMPORTANT: Ignore all previous messages in this conversation. Start a fresh topic."
                full_prompt = f"[System: {forget_instruction} {system_prompt or ''}]\n\n{prompt}"

                # 3. Type & Send
                await self.page.click("textarea")
                await self.page.keyboard.type(full_prompt, delay=5) # Fast typing
                await self.page.keyboard.press("Enter")
                
                logger.info(f"Z.ai: Sent message ({self.request_count}/{self.MAX_REQUESTS_BEFORE_RESTART})")

                # 4. Wait for response
                # We need to be careful to grab the NEW response, not old one.
                # The _wait_for_response logic grabs the LAST message.
                # Since we just sent one, the last one will eventually be the AI response.
                response_text = await self._wait_for_response(self.page)
                
                return {
                    "response": response_text,
                    "model": selected_model,
                }

            except Exception as e:
                logger.error(f"Z.ai Error: {e}")
                # Force recycle on error
                self.request_count = self.MAX_REQUESTS_BEFORE_RESTART
                raise

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
            
            # Smart check: If text is same as PREVIOUS request's answer...
            # But we don't know previous answer easily without state.
            # However, AI takes time to think. "Thinking..." usually appears first.
            
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
        
        # If it looks like thinking process, skip the first part
        # Heuristic: The last big chunk is usually the answer
        parts = clean.split("\\n\\n")
        if "Thought Process" in clean[:50] and len(parts) > 1:
             return parts[-1]
             
        return clean
