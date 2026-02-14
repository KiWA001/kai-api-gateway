"""
HuggingChat Provider (Browser-Based)
-------------------------------------
Uses Playwright Chromium to interact with https://huggingface.co/chat as a real browser.

Strategy:
- Reuses login sessions (saves cookies) - only login every 50 conversations
- Starts a new conversation for each API call (no context sharing)
- Supports model selection via the model dropdown
- Scrapes AI response from the DOM
"""

import asyncio
import logging
import re
from providers.base import BaseProvider
from config import PROVIDER_MODELS
from huggingchat_session import get_session_manager

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

    async def _perform_login(self, context) -> bool:
        """
        Perform fresh login to Hugging Face and save cookies.
        Returns True if login successful.
        """
        page = await context.new_page()
        session_mgr = get_session_manager()
        
        try:
            logger.info("HuggingChat: Performing fresh login...")
            await page.goto("https://huggingface.co/login", timeout=60000)
            
            # Wait for login form
            await page.wait_for_selector('input[name="username"]', timeout=10000)
            
            # Fill credentials
            await page.fill('input[name="username"]', HF_USERNAME)
            await asyncio.sleep(0.5)
            await page.fill('input[name="password"]', HF_PASSWORD)
            await asyncio.sleep(0.5)
            
            # Click login
            await page.click('button[type="submit"]')
            
            # Wait for navigation
            try:
                await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
            except:
                current_url = page.url
                if "login" in current_url:
                    logger.error("❌ HuggingChat: Login failed")
                    return False
            
            # Save cookies to session manager
            cookies = await context.cookies()
            session_mgr.set_cookies(cookies)
            session_mgr.save_session()
            
            logger.info("✅ HuggingChat: Login successful, session saved")
            await page.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ HuggingChat: Login error: {e}")
            await page.close()
            return False

    async def _start_new_chat(self, page):
        """Click 'New Chat' button to start a fresh conversation."""
        try:
            # Try multiple selectors for new chat button
            new_chat_selectors = [
                'a:has-text("New Chat")',
                'button:has-text("New Chat")',
                '[href="/chat/"]',  # Direct link to /chat
            ]
            
            for selector in new_chat_selectors:
                try:
                    btn = await page.wait_for_selector(selector, timeout=3000)
                    if btn:
                        await btn.click()
                        logger.info("HuggingChat: Started new conversation")
                        await asyncio.sleep(1.5)  # Wait for new chat to load
                        return True
                except:
                    continue
            
            # If button not found, navigate directly to /chat
            logger.info("HuggingChat: Navigating to /chat for new conversation")
            await page.goto("https://huggingface.co/chat", timeout=30000)
            await asyncio.sleep(2)
            return True
            
        except Exception as e:
            logger.warning(f"HuggingChat: Could not start new chat: {e}")
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
        session_mgr = get_session_manager()

        # Create context with cookies if we have them
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

        # Check if we need to login
        if session_mgr.needs_login():
            logger.info("HuggingChat: Session needs login")
            login_success = await self._perform_login(context)
            if not login_success:
                await context.close()
                raise RuntimeError("Failed to login to Hugging Face")
        else:
            # Use existing cookies
            cookies = session_mgr.get_cookies()
            if cookies:
                await context.add_cookies(cookies)
                logger.info(f"HuggingChat: Using existing session (conversation #{session_mgr._conversation_count + 1})")

        page = await context.new_page()

        try:
            logger.info(f"HuggingChat request: {selected_model}")

            # Navigate to HuggingChat
            await page.goto("https://huggingface.co/chat", timeout=60000)
            await asyncio.sleep(2)
            
            # Handle welcome modal if present (first time only)
            try:
                start_btn = await page.wait_for_selector(
                    'button:has-text("Start chatting")', 
                    timeout=3000
                )
                if start_btn:
                    logger.info("HuggingChat: Dismissing welcome modal...")
                    await start_btn.click()
                    await asyncio.sleep(2)
            except:
                pass
            
            # Start a new conversation (don't share context with previous messages)
            await self._start_new_chat(page)
            
            # Handle welcome modal again if it appears after new chat
            try:
                start_btn = await page.wait_for_selector(
                    'button:has-text("Start chatting")', 
                    timeout=3000
                )
                if start_btn:
                    await start_btn.click()
                    await asyncio.sleep(2)
            except:
                pass

            # If specific model requested (not omni), try to select it
            if selected_model and selected_model != "huggingface-omni":
                actual_model = selected_model.replace("huggingface-", "")
                await self._select_model(page, actual_model)

            await asyncio.sleep(self.HYDRATION_DELAY)

            # Find and use the chat input
            input_selector = None
            input_selectors = [
                'textarea[placeholder*="Ask"]',
                'textarea[placeholder*="Message"]',
                'textarea',
                '[contenteditable="true"]',
            ]
            
            for sel in input_selectors:
                try:
                    el = await page.wait_for_selector(sel, timeout=3000)
                    if el:
                        input_selector = sel
                        logger.info(f"HuggingChat: Found input using {sel}")
                        break
                except:
                    continue
            
            if not input_selector:
                raise RuntimeError("Could not find chat input field")

            # Type and send message
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"[System: {system_prompt}]\n\n{prompt}"

            await page.fill(input_selector, full_prompt)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            logger.info("HuggingChat: Message sent...")

            # Wait for response
            response_text = await self._wait_for_response(page)

            if not response_text:
                raise ValueError("Empty response from HuggingChat")

            # Save updated cookies and increment conversation count
            cookies = await context.cookies()
            session_mgr.set_cookies(cookies)
            session_mgr.increment_conversation()
            
            logger.info(f"HuggingChat: Conversation complete (total: {session_mgr._conversation_count})")

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            logger.error(f"HuggingChat Error: {e}")
            # If error might be session-related, clear it
            if "login" in str(e).lower() or "auth" in str(e).lower():
                session_mgr.clear_session()
            raise
        finally:
            await context.close()

    async def _select_model(self, page, model: str):
        """Try to select a specific model from the dropdown."""
        try:
            model_btn = await page.wait_for_selector(
                'button:has-text("Models")', 
                timeout=5000
            )
            if model_btn:
                await model_btn.click()
                await asyncio.sleep(1)
                
                model_option = await page.query_selector(f'text={model}')
                if model_option:
                    await model_option.click()
                    logger.info(f"HuggingChat: Selected model {model}")
                    await asyncio.sleep(1)
                else:
                    await page.keyboard.press("Escape")
                    logger.warning(f"HuggingChat: Model {model} not found")
        except Exception as e:
            logger.warning(f"HuggingChat: Could not select model: {e}")

    async def _wait_for_response(self, page) -> str:
        """Wait for and extract the AI response from the DOM."""
        last_text = ""
        stable_count = 0
        required_stable = 3

        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)

            # Check for loading/spinner
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
                    const selectors = [
                        '[data-message-role="assistant"]',
                        '.assistant-message',
                        '[class*="prose"]',
                        'article',
                        '.markdown-body',
                        '[class*="message-content"]',
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
        clean = re.sub(r"\n+\s*\n+", "\n\n", clean)
        return clean.strip()
