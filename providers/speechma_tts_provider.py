"""
SpeechMA TTS Provider
---------------------
Uses Playwright to automate speechma.com TTS generation.
Handles CAPTCHA solving via OCR and voice selection.
"""

import asyncio
import base64
import re
import time
from typing import Optional
from playwright.async_api import async_playwright, Page, ElementHandle
import io

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from ocr_utils import extract_digits_from_image


# SpeechMA Voice IDs mapping to their display names
SPEECHMA_VOICES = {
    "andrew": {"name": "Andrew Multilingual", "gender": "Male", "language": "Multilingual", "country": "United States"},
    "ava": {"name": "Ava Multilingual", "gender": "Female", "language": "Multilingual", "country": "United States"},
    "brian": {"name": "Brian Multilingual", "gender": "Male", "language": "Multilingual", "country": "United States"},
    "emma": {"name": "Emma Multilingual", "gender": "Female", "language": "Multilingual", "country": "United Kingdom"},
    "remy": {"name": "Remy Multilingual", "gender": "Male", "language": "Multilingual", "country": "France"},
    "vivienne": {"name": "Vivienne Multilingual", "gender": "Female", "language": "Multilingual", "country": "United States"},
    "daniel": {"name": "Daniel Multilingual", "gender": "Male", "language": "Multilingual", "country": "United Kingdom"},
    "serena": {"name": "Serena Multilingual", "gender": "Female", "language": "Multilingual", "country": "United States"},
    "matthew": {"name": "Matthew Multilingual", "gender": "Male", "language": "Multilingual", "country": "United States"},
    "jane": {"name": "Jane Multilingual", "gender": "Female", "language": "Multilingual", "country": "United States"},
    "alfonso": {"name": "Alfonso Multilingual", "gender": "Male", "language": "Multilingual", "country": "Spain"},
    "mario": {"name": "Mario Multilingual", "gender": "Male", "language": "Multilingual", "country": "Italy"},
    "klaus": {"name": "Klaus Multilingual", "gender": "Male", "language": "Multilingual", "country": "Germany"},
    "sakura": {"name": "Sakura Multilingual", "gender": "Female", "language": "Multilingual", "country": "Japan"},
    "xin": {"name": "Xin Multilingual", "gender": "Female", "language": "Multilingual", "country": "China"},
    "jose": {"name": "Jose Multilingual", "gender": "Male", "language": "Multilingual", "country": "Brazil"},
    "ines": {"name": "Ines Multilingual", "gender": "Female", "language": "Multilingual", "country": "Portugal"},
    "amira": {"name": "Amira Multilingual", "gender": "Female", "language": "Multilingual", "country": "Saudi Arabia"},
    "fatima": {"name": "Fatima Multilingual", "gender": "Female", "language": "Multilingual", "country": "UAE"},
}


class SpeechMATTSProvider:
    """SpeechMA Text-to-Speech Provider using Playwright automation."""
    
    def __init__(self):
        self.base_url = "https://speechma.com"
        self.default_voice = "ava"
        self.browser = None
        self.context = None
        
    def get_voice_info(self, voice_id: str) -> Optional[dict]:
        """Get voice information by voice_id."""
        voice_id_lower = voice_id.lower()
        
        # Try direct match first
        if voice_id_lower in SPEECHMA_VOICES:
            return {"voice_id": voice_id_lower, **SPEECHMA_VOICES[voice_id_lower]}
        
        # Try to find by partial match in name
        for vid, info in SPEECHMA_VOICES.items():
            if voice_id_lower in info["name"].lower():
                return {"voice_id": vid, **info}
        
        # Return default if not found
        return {"voice_id": self.default_voice, **SPEECHMA_VOICES[self.default_voice]}
    
    def get_available_voices(self) -> list[dict]:
        """Return all available voices."""
        return [{"voice_id": vid, **info} for vid, info in SPEECHMA_VOICES.items()]
    
    async def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent popup if present."""
        try:
            # Look for common cookie consent buttons
            consent_selectors = [
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                'button:has-text("Allow")',
                'button:has-text("Continue")',
                '.fc-button:has-text("Accept")',
                '[class*="consent"] button',
                '[class*="cookie"] button',
            ]
            
            for selector in consent_selectors:
                try:
                    btn = await page.wait_for_selector(selector, timeout=2000)
                    if btn:
                        await btn.click()
                        print("Cookie consent accepted")
                        await asyncio.sleep(0.5)
                        return
                except:
                    continue
        except:
            pass
    
    async def _extract_captcha_code(self, page: Page) -> Optional[str]:
        """
        Extract CAPTCHA code from the image using OCR.
        Returns the 5-digit code or None if failed.
        """
        try:
            # Find the CAPTCHA image element
            captcha_img = await page.wait_for_selector('img[alt="captcha"], .captcha-image, [class*="captcha"] img', timeout=5000)
            if not captcha_img:
                return None
            
            # Get the image src
            src = await captcha_img.get_attribute('src')
            if not src:
                return None
            
            # If it's a data URL, extract base64
            if src.startswith('data:image'):
                base64_data = src.split(',')[1]
                image_data = base64.b64decode(base64_data)
            else:
                # It's a relative URL, construct full URL
                if src.startswith('/'):
                    src = f"https://speechma.com{src}"
                # Otherwise download it
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(src) as response:
                        image_data = await response.read()
            
            # Use OCR utilities to extract digits
            code = await extract_digits_from_image(image_data, method="auto")
            return code
            
        except Exception as e:
            print(f"CAPTCHA extraction error: {e}")
            return None
    
    async def _refresh_captcha(self, page: Page) -> bool:
        """Click the refresh button to get a new CAPTCHA."""
        try:
            # Find and click refresh button
            refresh_btn = await page.query_selector('button[onclick*="refreshCaptcha"], button.captcha-refresh, button:has-text("↻")')
            if refresh_btn:
                await refresh_btn.click()
                await asyncio.sleep(1)
                return True
            
            # Try finding by icon/aria-label
            refresh_btn = await page.query_selector('button[aria-label*="refresh"], button[title*="refresh"]')
            if refresh_btn:
                await refresh_btn.click()
                await asyncio.sleep(1)
                return True
                
        except Exception as e:
            print(f"CAPTCHA refresh error: {e}")
        return False
    
    async def _select_voice(self, page: Page, voice_id: str) -> bool:
        """Select the specified voice."""
        try:
            voice_info = self.get_voice_info(voice_id)
            voice_name = voice_info["name"]
            
            # Handle any popup that might block clicking
            await self._handle_cookie_consent(page)
            
            # Wait for voice selection area to load
            await page.wait_for_selector('[class*="voice"]', timeout=10000)
            
            # Try clicking by text content
            try:
                # Use XPath for text matching
                voice_xpath = f'//*[contains(text(), "{voice_name}")]'
                voice_element = await page.wait_for_selector(f'xpath={voice_xpath}', timeout=5000)
                if voice_element:
                    await voice_element.click(force=True)  # Force click to bypass overlay
                    await asyncio.sleep(0.5)
                    return True
            except:
                pass
            
            # Try alternative selectors
            voice_cards = await page.query_selector_all('[class*="voice-card"], [class*="voice-item"], div[class*="voice"]')
            for card in voice_cards:
                try:
                    text = await card.inner_text()
                    if voice_name.lower() in text.lower():
                        await card.click(force=True)
                        await asyncio.sleep(0.5)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Voice selection error: {e}")
            return False
    
    async def _set_voice_effects(self, page: Page, pitch: int = 0, speed: int = 0, volume: int = 100) -> bool:
        """Set voice effects (pitch, speed, volume)."""
        try:
            # Click Voice Effects button
            effects_btn = await page.query_selector('button:has-text("Voice Effects"), [class*="voice-effects"]')
            if effects_btn:
                await effects_btn.click()
                await asyncio.sleep(0.5)
            
            # Set pitch if not 0
            if pitch != 0:
                pitch_input = await page.query_selector('input[placeholder*="pitch"], input[name*="pitch"], [class*="pitch"] input')
                if pitch_input:
                    await pitch_input.fill(str(pitch))
            
            # Set speed if not 0
            if speed != 0:
                speed_input = await page.query_selector('input[placeholder*="speed"], input[name*="speed"], [class*="speed"] input')
                if speed_input:
                    await speed_input.fill(str(speed))
            
            # Set volume
            if volume != 100:
                volume_input = await page.query_selector('input[placeholder*="volume"], input[name*="volume"], [class*="volume"] input')
                if volume_input:
                    await volume_input.fill(str(volume))
            
            return True
            
        except Exception as e:
            print(f"Voice effects error: {e}")
            return False
    
    async def generate_speech(
        self, 
        text: str, 
        voice_id: str = "ava",
        output_format: str = "mp3",
        pitch: int = 0,
        speed: int = 0,
        volume: int = 100
    ) -> Optional[bytes]:
        """
        Generate speech from text using SpeechMA.
        
        Args:
            text: Text to convert to speech (max 2000 chars)
            voice_id: Voice ID to use
            output_format: Output audio format
            pitch: Voice pitch adjustment (-10 to 10)
            speed: Speech speed adjustment (-10 to 10)
            volume: Volume percentage (0-200)
            
        Returns:
            Audio data as bytes or None if failed
        """
        # Limit text length
        if len(text) > 2000:
            text = text[:2000]
        
        async with async_playwright() as p:
            browser = None
            try:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                
                # Navigate to SpeechMA
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(3)  # Wait for page to fully load (including any popups)
                
                # Handle cookie consent popup
                await self._handle_cookie_consent(page)
                
                # Enter text - use a more robust selector
                text_area = None
                text_selectors = [
                    'textarea[placeholder*="text" i]',
                    'textarea[name*="text" i]',
                    '#text-input',
                    'textarea',
                    '[contenteditable*="true"]',
                ]
                
                for selector in text_selectors:
                    try:
                        text_area = await page.wait_for_selector(selector, timeout=5000)
                        if text_area:
                            print(f"Found text area with selector: {selector}")
                            break
                    except:
                        continue
                
                if not text_area:
                    raise Exception("Could not find text input area")
                
                # Clear and fill
                await text_area.fill("")
                await asyncio.sleep(0.2)
                await text_area.fill(text)
                await asyncio.sleep(0.5)
                
                # Select voice
                voice_selected = await self._select_voice(page, voice_id)
                if not voice_selected:
                    print(f"Warning: Could not select voice {voice_id}, using default")
                
                # Set voice effects if needed
                if pitch != 0 or speed != 0 or volume != 100:
                    await self._set_voice_effects(page, pitch, speed, volume)
                
                # Solve CAPTCHA
                max_captcha_attempts = 5
                captcha_solved = False
                
                for attempt in range(max_captcha_attempts):
                    # Extract CAPTCHA code
                    captcha_code = await self._extract_captcha_code(page)
                    
                    if captcha_code and len(captcha_code) == 5:
                        print(f"CAPTCHA code extracted: {captcha_code}")
                        # Enter CAPTCHA - find input fresh each time
                        captcha_selectors = [
                            'input[placeholder*="captcha" i]',
                            'input[name*="captcha" i]',
                            '#captcha-input',
                            'input[type="text"]:not([name*="text" i])',
                        ]
                        
                        captcha_input = None
                        for sel in captcha_selectors:
                            try:
                                captcha_input = await page.wait_for_selector(sel, timeout=3000)
                                if captcha_input:
                                    print(f"Found CAPTCHA input with: {sel}")
                                    break
                            except:
                                continue
                        
                        if captcha_input:
                            await captcha_input.fill(captcha_code)
                            await asyncio.sleep(0.5)
                            captcha_solved = True
                            break
                        else:
                            print("Could not find CAPTCHA input field")
                    else:
                        print(f"CAPTCHA extraction failed (attempt {attempt + 1})")
                    
                    # If CAPTCHA extraction failed, try refreshing
                    if attempt < max_captcha_attempts - 1:
                        refreshed = await self._refresh_captcha(page)
                        if refreshed:
                            await asyncio.sleep(3)  # Wait for new CAPTCHA
                            continue
                        else:
                            print("Could not refresh CAPTCHA, trying again...")
                            await asyncio.sleep(2)
                
                if not captcha_solved:
                    raise Exception("Could not solve CAPTCHA after multiple attempts")
                
                # Click Generate Audio button
                generate_btn = await page.wait_for_selector('button:has-text("Generate Audio"), button[type="submit"]', timeout=10000)
                if not generate_btn:
                    raise Exception("Could not find Generate Audio button")
                
                # Set up download handler before clicking
                download_future = asyncio.Future()
                
                async def handle_download(download):
                    try:
                        path = await download.path()
                        with open(path, 'rb') as f:
                            data = f.read()
                        download_future.set_result(data)
                    except Exception as e:
                        download_future.set_exception(e)
                
                page.on('download', lambda d: asyncio.create_task(handle_download(d)))
                
                # Click generate
                await generate_btn.click()
                
                # Wait for generation and download
                try:
                    audio_data = await asyncio.wait_for(download_future, timeout=60)
                    return audio_data
                except asyncio.TimeoutError:
                    # Alternative: Try to get audio from audio player element
                    audio_element = await page.wait_for_selector('audio[src], source[type="audio/mp3"]', timeout=10000)
                    if audio_element:
                        audio_src = await audio_element.get_attribute('src')
                        if audio_src:
                            # Download audio from URL
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.get(audio_src) as response:
                                    return await response.read()
                    
                    raise Exception("Audio generation timeout - download not detected")
                
            except Exception as e:
                print(f"SpeechMA generation error: {e}")
                return None
                
            finally:
                if browser:
                    await browser.close()
    
    async def health_check(self) -> bool:
        """Check if SpeechMA is accessible."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(self.base_url, timeout=30000)
                await browser.close()
                return True
        except Exception:
            return False


# Global provider instance
_speechma_provider = None

def get_speechma_provider() -> SpeechMATTSProvider:
    """Get or create the SpeechMA provider singleton."""
    global _speechma_provider
    if _speechma_provider is None:
        _speechma_provider = SpeechMATTSProvider()
    return _speechma_provider
