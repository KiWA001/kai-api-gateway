"""
Hugging Face Widget Provider (Mini Chat)
----------------------------------------
Uses Playwright to interact with the mini chat widget on Hugging Face model pages.
The widget is often in an iframe, so we need to handle that.

Strategy:
- Single persistent browser instance
- Navigate to model page and use the mini chat widget (in iframe)
- Start new chat by clearing/refreshing the widget
- Supports 10+ popular models
"""

import asyncio
import logging
import re
from typing import Optional
from providers.base import BaseProvider
from config import PROVIDER_MODELS

logger = logging.getLogger("kai_api.huggingface_widget")

_playwright = None
_browser = None
_context = None
_lock = asyncio.Lock()
_is_initialized = False

# Hugging Face credentials (same as HuggingChat)
HF_USERNAME = "one@bo5.store"
HF_PASSWORD = "Zzzzz1$."

# Top 10+ Popular models with their HF paths
POPULAR_MODELS = {
    # Tier 1 - Most Popular
    "hf-kimi-k2.5": "moonshotai/Kimi-K2.5",
    "hf-minimax-m2.5": "MiniMaxAI/MiniMax-M2.5",
    "hf-glm-5": "zai-org/GLM-5",
    "hf-llama-4-scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "hf-llama-4-maverick": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    "hf-llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct",
    "hf-deepseek-v3": "deepseek-ai/DeepSeek-V3",
    "hf-qwen3-32b": "Qwen/Qwen3-32B",
    "hf-qwen2.5-72b": "Qwen/Qwen2.5-72B-Instruct",
    "hf-phi-4": "microsoft/Phi-4",
}


class HuggingFaceWidgetProvider(BaseProvider):
    """AI provider using Hugging Face model mini chat widgets."""

    RESPONSE_TIMEOUT = 90
    HYDRATION_DELAY = 2.0

    @property
    def name(self) -> str:
        return "huggingface_widget"

    def get_available_models(self) -> list[str]:
        return list(POPULAR_MODELS.keys())

    @staticmethod
    def is_available() -> bool:
        """Check if Playwright is installed."""
        try:
            from playwright.async_api import async_playwright
            return True
        except ImportError:
            return False

    async def _ensure_browser(self):
        """Start persistent browser and context if not running."""
        global _playwright, _browser, _context

        async with _lock:
            if _browser and _browser.is_connected():
                return

            logger.info("🚀 HuggingFace Widget: Launching browser...")
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
            
            # Create persistent context (cookies persist across requests)
            _context = await _browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )

            # Hide webdriver
            await _context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            logger.info("✅ HuggingFace Widget: Browser ready")

    async def _ensure_logged_in(self):
        """Check if logged in, if not perform login."""
        global _context
        
        page = await _context.new_page()
        try:
            # Check if we're logged in by going to a model page
            await page.goto("https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct", timeout=30000)
            await asyncio.sleep(1)
            
            # Check for login button
            login_btn = await page.query_selector('a[href*="login"], button:has-text("Log in")')
            
            if login_btn:
                logger.info("HF Widget: Not logged in, performing login...")
                await self._perform_login()
            else:
                logger.info("HF Widget: Already logged in")
                
        except Exception as e:
            logger.warning(f"HF Widget: Login check failed: {e}")
        finally:
            await page.close()

    async def _perform_login(self):
        """Login to Hugging Face."""
        global _context
        
        page = await _context.new_page()
        try:
            logger.info("HF Widget: Logging in...")
            await page.goto("https://huggingface.co/login", timeout=60000)
            
            # Fill credentials
            await page.wait_for_selector('input[name="username"]', timeout=10000)
            await page.fill('input[name="username"]', HF_USERNAME)
            await asyncio.sleep(0.3)
            await page.fill('input[name="password"]', HF_PASSWORD)
            await asyncio.sleep(0.3)
            
            # Submit
            await page.click('button[type="submit"]')
            
            # Wait for redirect
            try:
                await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
                logger.info("✅ HF Widget: Login successful")
            except:
                current_url = page.url
                if "login" in current_url:
                    logger.error("❌ HF Widget: Login failed")
                    raise RuntimeError("Failed to login to Hugging Face")
                    
        finally:
            await page.close()

    async def _find_widget_frame(self, page):
        """Find the iframe containing the chat widget."""
        # HF widgets are often in iframes
        frames = page.frames
        
        for frame in frames:
            try:
                # Check if this frame has the widget
                widget = await frame.query_selector('textarea, [contenteditable="true"], .chat-input')
                if widget:
                    logger.info(f"HF Widget: Found widget in frame: {frame.url[:60]}...")
                    return frame
            except:
                continue
        
        # If no iframe found, use main page
        return page

    async def send_message(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict:
        """Send message via Hugging Face model widget."""
        if not self.is_available():
            raise RuntimeError("Playwright not installed")

        await self._ensure_browser()
        await self._ensure_logged_in()

        global _context

        # Get model path
        selected_model = model or "hf-kimi-k2.5"
        model_path = POPULAR_MODELS.get(selected_model, selected_model.replace("hf-", ""))
        
        if selected_model not in POPULAR_MODELS:
            selected_model = "hf-kimi-k2.5"
            model_path = POPULAR_MODELS[selected_model]

        logger.info(f"HF Widget request: {selected_model} ({model_path})")

        page = await _context.new_page()

        try:
            # Navigate to model page
            url = f"https://huggingface.co/{model_path}"
            await page.goto(url, timeout=60000)
            await asyncio.sleep(self.HYDRATION_DELAY)

            # Handle cookie consent if present
            try:
                cookie_btn = await page.wait_for_selector(
                    'button:has-text("Accept"), button:has-text("Accept all"), button:has-text("I agree")', 
                    timeout=3000
                )
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(0.5)
                    logger.info("HF Widget: Accepted cookies")
            except:
                pass

            # Scroll down to load the widget
            logger.info("HF Widget: Scrolling to find widget...")
            await page.evaluate("window.scrollTo(0, 600)")
            await asyncio.sleep(2)

            # Find the widget frame (might be in iframe)
            widget_frame = await self._find_widget_frame(page)
            
            # Find the input field in the widget
            input_selectors = [
                'textarea[placeholder*="message" i]',
                'textarea[placeholder*="chat" i]',
                'textarea[placeholder*="ask" i]',
                'textarea',
                '[contenteditable="true"]',
                '[role="textbox"]',
                'input[type="text"]',
                '.chat-input',
                '[class*="input"]',
            ]

            input_element = None
            for sel in input_selectors:
                try:
                    if widget_frame == page:
                        el = await page.wait_for_selector(sel, timeout=2000)
                    else:
                        el = await widget_frame.wait_for_selector(sel, timeout=2000)
                    
                    if el:
                        input_element = el
                        logger.info(f"HF Widget: Found input using: {sel}")
                        break
                except:
                    continue

            if not input_element:
                # Try scrolling more and try again
                await page.evaluate("window.scrollTo(0, 1000)")
                await asyncio.sleep(2)
                
                for sel in input_selectors:
                    try:
                        if widget_frame == page:
                            el = await page.wait_for_selector(sel, timeout=3000)
                        else:
                            el = await widget_frame.wait_for_selector(sel, timeout=3000)
                        
                        if el:
                            input_element = el
                            logger.info(f"HF Widget: Found input on retry using: {sel}")
                            break
                    except:
                        continue

            if not input_element:
                raise RuntimeError("Could not find chat widget input field")

            # Clear any existing conversation
            await self._clear_chat(widget_frame or page)

            # Type message
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"[System: {system_prompt}]\n\n{prompt}"

            await input_element.fill(full_prompt)
            await asyncio.sleep(0.5)

            # Submit - try multiple methods
            submitted = False
            
            # Method 1: Look for send button
            send_selectors = [
                'button[type="submit"]',
                'button:has-text("Send")',
                'button:has([aria-label*="send"])',
                '[class*="send"]',
                'button svg',  # Often just an icon button
            ]
            
            for sel in send_selectors:
                try:
                    if widget_frame == page:
                        send_btn = await page.query_selector(sel)
                    else:
                        send_btn = await widget_frame.query_selector(sel)
                    
                    if send_btn:
                        await send_btn.click()
                        submitted = True
                        logger.info("HF Widget: Clicked send button")
                        break
                except:
                    continue
            
            # Method 2: Press Enter
            if not submitted:
                await input_element.press("Enter")
                logger.info("HF Widget: Pressed Enter to submit")

            logger.info("HF Widget: Message sent, waiting for response...")

            # Wait for response
            response_text = await self._wait_for_response(widget_frame or page)

            if not response_text:
                raise ValueError("Empty response from model")

            logger.info(f"HF Widget: Got response ({len(response_text)} chars)")

            return {
                "response": response_text,
                "model": selected_model,
            }

        except Exception as e:
            logger.error(f"HF Widget Error: {e}")
            raise
        finally:
            await page.close()

    async def _clear_chat(self, frame):
        """Clear existing chat to start fresh conversation."""
        try:
            # Look for clear/new chat button
            clear_selectors = [
                'button:has-text("Clear")',
                'button:has-text("New")',
                'button:has-text("Reset")',
                '[class*="clear"]',
                '[class*="new-chat"]',
                'button svg[data-icon*="trash"]',
            ]

            for sel in clear_selectors:
                try:
                    btn = await frame.wait_for_selector(sel, timeout=2000)
                    if btn:
                        await btn.click()
                        logger.info("HF Widget: Cleared previous chat")
                        await asyncio.sleep(0.5)
                        return
                except:
                    continue

        except Exception as e:
            logger.warning(f"HF Widget: Could not clear chat: {e}")

    async def _wait_for_response(self, frame) -> str:
        """Wait for and extract response from widget."""
        last_text = ""
        stable_count = 0
        required_stable = 3  # Need more stability for HF widgets

        for i in range(self.RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)

            # Check if still loading/generating
            try:
                is_loading = await frame.evaluate("""
                    () => {
                        const loading = document.querySelectorAll(
                            '[class*="loading" i], [class*="spinner" i], [class*="animate" i], ' +
                            '[data-loading="true"], .generating, [class*="streaming" i]'
                        );
                        return loading.length > 0;
                    }
                """)

                if is_loading:
                    continue
            except:
                pass

            # Extract response text from the widget specifically
            try:
                current_text = await frame.evaluate("""
                    () => {
                        // HF widgets often have a specific structure - look for the chat container first
                        const widgetContainers = [
                            document.querySelector('.inference-widget'),
                            document.querySelector('[data-target="InferenceWidget"]'),
                            document.querySelector('.widget-container'),
                            document.querySelector('[class*="widget"]'),
                        ].filter(Boolean);
                        
                        // Search within widget containers first
                        for (const container of widgetContainers) {
                            // Look for assistant responses within the widget
                            const assistantMsgs = container.querySelectorAll('[data-role="assistant"], .assistant-message, .ai-message, [class*="assistant"]');
                            if (assistantMsgs.length > 0) {
                                const last = assistantMsgs[assistantMsgs.length - 1];
                                const text = last.innerText || last.textContent || '';
                                if (text.trim().length > 10 && !text.includes('Changelog')) return text.trim();
                            }
                            
                            // Look for message bubbles
                            const messages = container.querySelectorAll('.message, [class*="message"]');
                            for (let i = messages.length - 1; i >= 0; i--) {
                                const msg = messages[i];
                                // Check if it's not a user message
                                const isUser = msg.classList.contains('user') || 
                                              msg.getAttribute('data-role') === 'user' ||
                                              msg.querySelector('.user, [data-role="user"]') !== null;
                                if (!isUser) {
                                    const text = msg.innerText || msg.textContent || '';
                                    // Filter out model card content
                                    if (text.trim().length > 10 && 
                                        !text.includes('Changelog') && 
                                        !text.includes('Model Introduction') &&
                                        !text.includes('Parameters') &&
                                        !text.includes('Architecture')) {
                                        return text.trim();
                                    }
                                }
                            }
                        }
                        
                        // Last resort: look for recently added content
                        const allDivs = document.querySelectorAll('div');
                        for (let i = allDivs.length - 1; i >= Math.max(0, allDivs.length - 20); i--) {
                            const div = allDivs[i];
                            const text = div.innerText || div.textContent || '';
                            if (text.trim().length > 20 && 
                                text.trim().length < 500 && // Reasonable response length
                                !text.includes('Changelog') &&
                                !text.includes('License') &&
                                !text.includes('Parameters') &&
                                !div.querySelector('h1, h2, h3, table')) { // Not a header or table
                                return text.trim();
                            }
                        }
                        
                        return '';
                    }
                """)
            except:
                current_text = ""

            if not current_text:
                continue

            clean = self._clean_response(current_text)

            if clean == last_text and len(clean) > 10:
                stable_count += 1
                if stable_count >= required_stable:
                    return clean
            else:
                stable_count = 0
                last_text = clean

            if i % 10 == 9:
                logger.info(f"HF Widget: Streaming... {len(last_text)} chars")

        if last_text:
            logger.warning("HF Widget: Timeout, returning partial response")
            return last_text

        raise TimeoutError("No response from model")

    def _clean_response(self, text: str) -> str:
        """Clean up response text."""
        clean = text.strip()
        # Remove common artifacts
        clean = re.sub(r"\n+\s*\n+", "\n\n", clean)
        clean = re.sub(r"^User:\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^You:\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^Assistant:\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^AI:\s*", "", clean, flags=re.IGNORECASE)
        return clean.strip()

    async def health_check(self) -> bool:
        """Quick health check."""
        try:
            if not self.is_available():
                return False
            await self._ensure_browser()
            return _browser.is_connected()
        except Exception:
            return False
