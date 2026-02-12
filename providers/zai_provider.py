"""
Z.ai Provider (Browser-Based)
------------------------------
Uses Playwright Chromium to interact with https://chat.z.ai/ as a real browser.

Strategy:
- Keeps a persistent browser context alive (singleton page)
- Types messages into the textarea, presses Enter
- Scrapes the AI response from the DOM
- Captures network requests for analytics/reverse engineering

Why browser-based?
- Z.ai uses a proprietary x-signature hash + fingerprinting in query params
- The signature algorithm is obfuscated in their JS bundle
- Browser-as-proxy is self-healing: uses Z.ai's own JS to generate valid signatures

Limitations:
- Requires Playwright + Chromium binaries (won't work on Vercel serverless)
- Slower than direct API calls (~5-15s per message)
- One request at a time (browser is single-threaded)

Models available:
- glm-5 (default, best quality)
- glm-4-flash (faster, lower quality)
"""

import asyncio
import logging
import time
import json
from providers.base import BaseProvider
from config import PROVIDER_MODELS

logger = logging.getLogger("kai_api.zai")

# Singleton browser instance
_browser_instance = None
_browser_lock = asyncio.Lock()


class ZaiProvider(BaseProvider):
    """AI provider using Z.ai via Playwright browser automation."""

    # How long to wait for AI response in DOM (seconds)
    RESPONSE_TIMEOUT = 45
    # How long to wait after page load for JS hydration
    HYDRATION_DELAY = 3

    @property
    def name(self) -> str:
        return "zai"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("zai", [])

    @staticmethod
    def is_available() -> bool:
        """Check if Playwright is installed and usable."""
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False

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
        1. Get or create a browser page (singleton)
        2. If page has an existing chat, start a new one
        3. Type the prompt, press Enter
        4. Wait for AI response in DOM
        5. Scrape and return the response text
        """
        if not self.is_available():
            raise RuntimeError("Playwright not installed. Install with: pip install playwright && python -m playwright install chromium")

        selected_model = model or "glm-5"

        # Run browser interaction in executor (Playwright sync API)
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(
            None,
            self._browser_chat,
            prompt,
            selected_model,
            system_prompt,
        )

        if not response_text:
            raise ValueError("Z.ai returned empty response")

        return {
            "response": response_text,
            "model": selected_model,
        }

    def _browser_chat(self, prompt: str, model: str, system_prompt: str | None) -> str:
        """
        Synchronous browser interaction (runs in thread executor).

        Uses a fresh page per request to avoid state issues.
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            # Hide webdriver flag
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            page = context.new_page()

            try:
                # Step 1: Load page
                logger.info("Z.ai: Loading page...")
                page.goto("https://chat.z.ai/", timeout=60000)
                page.wait_for_selector("textarea", timeout=60000)
                time.sleep(self.HYDRATION_DELAY)

                # Step 2: If model selection is needed, try to switch
                # (For now, Z.ai defaults to glm-5 which is what we want)

                # Step 3: Type and send
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"[System: {system_prompt}]\n\n{prompt}"

                textarea = page.query_selector("textarea")
                textarea.click()
                page.keyboard.type(full_prompt, delay=15)
                time.sleep(0.3)
                page.keyboard.press("Enter")
                logger.info("Z.ai: Message sent, waiting for response...")

                # Step 4: Wait for response in DOM
                response_text = self._wait_for_response(page)

                return response_text

            except Exception as e:
                logger.error(f"Z.ai browser error: {e}")
                raise
            finally:
                browser.close()

    def _wait_for_response(self, page) -> str:
        """
        Poll the DOM until the AI response appears and stabilizes.
        Returns the extracted response text.
        """
        last_text = ""
        stable_count = 0
        required_stable = 3  # Text must be unchanged for 3 consecutive checks

        for i in range(self.RESPONSE_TIMEOUT * 2):  # Check every 0.5s
            time.sleep(0.5)

            current_text = page.evaluate("""
                () => {
                    // Z.ai renders responses in elements with 'prose' class
                    // or various message containers
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
                            if (text.trim().length > 0) {
                                return text.trim();
                            }
                        }
                    }
                    return '';
                }
            """)

            if not current_text:
                continue

            # Remove "Thinking..." prefix if present
            clean = current_text
            for prefix in ["Thinking...\nSkip\n", "Thinking...\n"]:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]

            if clean == last_text and len(clean) > 0:
                stable_count += 1
                if stable_count >= required_stable:
                    # Response has stabilized — extract final answer
                    return self._extract_final_answer(clean)
            else:
                stable_count = 0
                last_text = clean

            # Log progress every 5 seconds
            if i % 10 == 9:
                logger.info(f"Z.ai: Waiting... ({(i+1)/2:.0f}s, {len(last_text)} chars so far)")

        # Timeout — return whatever we have
        if last_text:
            logger.warning(f"Z.ai: Timeout, returning partial response ({len(last_text)} chars)")
            return self._extract_final_answer(last_text)

        raise TimeoutError(f"Z.ai did not respond within {self.RESPONSE_TIMEOUT}s")

    def _extract_final_answer(self, text: str) -> str:
        """
        Extract just the final answer from Z.ai response.
        Z.ai's GLM-5 thinking model outputs reasoning + answer.
        We want only the answer portion.
        """
        # Strip common prefixes
        clean = text.strip()
        
        for prefix in ["Thinking...\nSkip\n", "Thinking...\n"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]

        # Try to find the boundary between thinking and answer
        thinking_markers = [
            "Thought Process\n",
            "Analysis\n",
            "Reasoning\n",
            "Step-by-step\n",
        ]
        
        candidates = []
        
        # Strategy 1: Split by Thinking Markers
        for marker in thinking_markers:
            if clean.startswith(marker):
                # The thinking block usually ends with a double newline
                # But sometimes it's hard to tell where thinking ends and answer begins.
                # However, usually the answer is at the very end.
                parts = clean.split("\n\n")
                
                # Filter out the "Thought Process" header part if it's the first one
                if parts and marker.strip() in parts[0]:
                    parts = parts[1:]
                
                candidates = parts
                break
        
        if not candidates:
            candidates = clean.split("\n\n")

        # Reverse iterate to find the best "Answer" candidate
        # We need to skip UI artifacts like "Here is the breakdown:\nStrawberry"
        for i in range(len(candidates) - 1, -1, -1):
            para = candidates[i].strip()
            if not para:
                continue
            
            # Heuristics to skip UI noise:
            # 1. Very short and ends with colon (e.g. "Here is the breakdown:")
            if len(para) < 30 and para.endswith(":"):
                continue
            # 2. Just one or two words (likely a label or artifact)
            if len(para.split()) < 3 and not para.endswith((".", "!", "?", '"')):
                continue
            # 3. Specific UI strings seen in Z.ai
            if "Here is the breakdown" in para or "Strawberry" == para:
                continue
                
            return para
            
        # Fallback: return the whole cleaned text if we couldn't find a specific paragraph
        return clean
