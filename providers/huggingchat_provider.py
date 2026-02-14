"""
HuggingChat Provider (Browser-Based)
-------------------------------------
Uses Playwright Chromium to interact with https://huggingface.co/chat as a real browser.

Strategy:
- Handles login with provided credentials
- Saves session cookies for reuse
- Supports model selection via the model dropdown
- Scrapes AI response from the DOM
"""

import asyncio
import logging
import re
from providers.base import BaseProvider
from config import PROVIDER_MODELS

logger = logging.getLogger("kai_api.huggingchat")

_playwright = None
_browser = None
_lock = asyncio.Lock()

# Hugging Face credentials
HF_USERNAME = "one@bo5.store"
HF_PASSWORD = "Zzzzz1$."


class HuggingChatProvider(BaseProvider):
    """AI provider using HuggingChat via Persistent Playwright Browser."""

    RESPONSE_TIMEOUT = 90
    HYDRATION_DELAY = 2.0

    @property
    def name(self) -> str:
        return "huggingchat"

    def get_available_models(self) -> list[str]:
        return PROVIDER_MODELS.get("huggingchat", ["huggingface-omni"])

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

            logger.info("🚀 HuggingChat: Launching Persistent Browser...")
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
            logger.info("✅ HuggingChat: Browser is Ready.")

    async def _login(self, context) -> bool:
        """
        Perform login to Hugging Face.
        Returns True if login successful.
        """
        page = await context.new_page()
        
        try:
            logger.info("HuggingChat: Navigating to login page...")
            await page.goto("https://huggingface.co/login", timeout=60000)
            
            # Wait for login form
            await page.wait_for_selector('input[name="username"]', timeout=10000)
            
            logger.info("HuggingChat: Filling login credentials...")
            
            # Fill username/email
            await page.fill('input[name="username"]', HF_USERNAME)
            await asyncio.sleep(0.5)
            
            # Fill password
            await page.fill('input[name="password"]', HF_PASSWORD)
            await asyncio.sleep(0.5)
            
            # Click login button
            await page.click('button[type="submit"]')
            
            # Wait for navigation after login
            try:
                await page.wait_for_url("https://huggingface.co/", timeout=10000)
                logger.info("✅ HuggingChat: Login successful!")
                await page.close()
                return True
            except:
                # Check if we're still on login page (login failed)
                current_url = page.url
                if "login" in current_url:
                    logger.error("❌ HuggingChat: Login failed - still on login page")
                    await page.close()
                    return False
                else:
                    logger.info("✅ HuggingChat: Login successful (redirected)")
                    await page.close()
                    return True
                    
        except Exception as e:
            logger.error(f"❌ HuggingChat: Login error: {e}")
            await page.close()
            return False

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """Send a message via HuggingChat browser automation."""
        if not self.is_available():
            raise RuntimeError("Playwright not installed.")

        await self._ensure_browser()
        selected_model = model or "huggingface-omni"

        # Create persistent context (for session/cookies)
        context = await _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )

        # Hide webdriver flag
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        # Try to login first
        login_success = await self._login(context)
        if not login_success:
            await context.close()
            raise RuntimeError("Failed to login to Hugging Face. Check credentials.")

        page = await context.new_page()

        try:
            logger.info(f"HuggingChat request: {selected_model}")

            # Navigate to HuggingChat
            await page.goto("https://huggingface.co/chat", timeout=60000)
            
            # Wait for chat interface to load
            await asyncio.sleep(2)

            # If specific model requested (not omni), try to select it
            if selected_model and selected_model != "huggingface-omni":
                # Extract actual model name from prefixed name
                actual_model = selected_model.replace("huggingface-", "")
                await self._select_model(page, actual_model)

            await asyncio.sleep(self.HYDRATION_DELAY)

            # Find and use the chat input
            input_selector = 'textarea[placeholder*="Ask anything"]'
            
            try:
                await page.wait_for_selector(input_selector, timeout=10000)
            except:
                # Fallback selectors
                input_selector = 'textarea'
                await page.wait_for_selector(input_selector, timeout=5000)

            # Type the message
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"[System: {system_prompt}]\n\n{prompt}"

            await page.fill(input_selector, full_prompt)
            await asyncio.sleep(0.5)
            
            # Press Enter to send
            await page.keyboard.press("Enter")
            logger.info("HuggingChat: Message sent...")

            # Wait for response
            response_text = await self._wait_for_response(page)

            if not response_text:
                raise ValueError("Empty response from HuggingChat")

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            logger.error(f"HuggingChat Error: {e}")
            raise
        finally:
            await context.close()

    async def _select_model(self, page, model: str):
        """Try to select a specific model from the dropdown."""
        try:
            # Click the model selector button
            model_btn = await page.wait_for_selector(
                'button:has-text("Models")', 
                timeout=5000
            )
            if model_btn:
                await model_btn.click()
                await asyncio.sleep(1)
                
                # Try to find and click the specific model
                # Model names in HuggingChat are full paths like "meta-llama/Llama-3.3-70B-Instruct"
                model_option = await page.query_selector(
                    f'text={model}'
                )
                if model_option:
                    await model_option.click()
                    logger.info(f"HuggingChat: Selected model {model}")
                    await asyncio.sleep(1)
                else:
                    # Close dropdown if model not found
                    await page.keyboard.press("Escape")
                    logger.warning(f"HuggingChat: Model {model} not found, using default")
        except Exception as e:
            logger.warning(f"HuggingChat: Could not select model: {e}")

    async def _wait_for_response(self, page) -> str:
        """Wait for and extract the AI response from the DOM."""
        last_text = ""
        stable_count = 0
        required_stable = 3

        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)

            # Check for loading/spinner and skip
            is_loading = await page.evaluate("""
                () => {
                    const spinners = document.querySelectorAll('[class*="loading"], [class*="spinner"], .animate-pulse');
                    return spinners.length > 0;
                }
            """)
            
            if is_loading:
                continue

            # Extract response text
            current_text = await page.evaluate("""
                () => {
                    // Look for the last assistant message
                    const selectors = [
                        '[data-message-role="assistant"]',
                        '.assistant-message',
                        '[class*="prose"]',
                        'article',
                        '.markdown-body',
                        '[class*="message-content"]',
                        '.chat-message:last-child .content',
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
                logger.info(f"HuggingChat: Stream... {len(last_text)} chars")

        if last_text:
            logger.warning("HuggingChat: Timeout, returning partial.")
            return last_text

        raise TimeoutError("HuggingChat no response")

    def _clean_response(self, text: str) -> str:
        """Clean up HuggingChat response text."""
        clean = text.strip()
        
        # Remove common artifacts
        clean = re.sub(r"\n+\s*\n+", "\n\n", clean)
        
        return clean.strip()
