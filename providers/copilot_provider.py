"""
Microsoft Copilot Provider (Browser-Based)
-------------------------------------------
Uses Playwright Chromium to interact with https://copilot.microsoft.com/ as a real browser.

Strategy:
- Reuses the global Playwright browser instance (shared pattern with Z.ai/Gemini).
- Uses EPHEMERAL contexts (Tabs) per request for robust data isolation.
- Scrapes the AI response from the DOM.
- Handles the "Continue" button for longer responses.
"""

import asyncio
import logging
import re
from providers.base import BaseProvider
from config import PROVIDER_MODELS

logger = logging.getLogger("kai_api.copilot")

_playwright = None
_browser = None
_lock = asyncio.Lock()


class CopilotProvider(BaseProvider):
    """AI provider using Microsoft Copilot via Persistent Playwright Browser."""

    RESPONSE_TIMEOUT = 60
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

        # Create Ephemeral Context
        context = await _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Hide webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        try:
            logger.info(f"Copilot request: {selected_model}")

            # Navigate to Copilot
            await page.goto("https://copilot.microsoft.com/", timeout=60000)

            # Wait for the chat input to be ready
            # Copilot uses contenteditable divs
            input_selectors = [
                '[data-testid="chat-input"]',
                'div[contenteditable="true"]',
                '[role="textbox"]',
                'textarea',
                '.input-area div[contenteditable]',
            ]

            input_selector = None
            for sel in input_selectors:
                try:
                    await page.wait_for_selector(sel, timeout=10000)
                    input_selector = sel
                    logger.info(f"✅ Copilot: Found input selector: {sel}")
                    break
                except:
                    continue

            if not input_selector:
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

            logger.info("Copilot: Message sent...")

            # Wait for response
            response_text = await self._wait_for_response(page)

            if not response_text:
                raise ValueError("Empty response from Copilot")

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            logger.error(f"Copilot Error: {e}")
            raise
        finally:
            await context.close()

    async def _wait_for_response(self, page) -> str:
        """Wait for and extract the AI response from the DOM."""
        last_text = ""
        stable_count = 0
        required_stable = 4

        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)

            # Check for "Continue" button and click it
            try:
                continue_btn = await page.query_selector(
                    'button:has-text("Continue"), button:has-text("Continue anyway")'
                )
                if continue_btn and await continue_btn.is_visible():
                    logger.info("Copilot: Clicking 'Continue' button...")
                    await continue_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

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
