"""
Debug HuggingChat with screenshots
"""

import asyncio
import os
from playwright.async_api import async_playwright

HF_USERNAME = "one@bo5.store"
HF_PASSWORD = "Zzzzz1$."


async def debug_with_screenshots():
    """Debug HuggingChat and save screenshots at each step."""
    print("🔍 Debugging HuggingChat with screenshots...\n")
    
    os.makedirs("debug_screenshots", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )

        page = await context.new_page()

        # Step 1: Login page
        print("1. Loading login page...")
        await page.goto("https://huggingface.co/login", timeout=60000)
        await page.screenshot(path="debug_screenshots/hf_login_page.png")
        print("   ✓ Screenshot: hf_login_page.png")

        # Step 2: Fill credentials
        print("2. Filling credentials...")
        await page.fill('input[name="username"]', HF_USERNAME)
        await page.fill('input[name="password"]', HF_PASSWORD)
        await page.screenshot(path="debug_screenshots/hf_login_filled.png")
        print("   ✓ Screenshot: hf_login_filled.png")

        # Step 3: Submit login
        print("3. Submitting login...")
        await page.click('button[type="submit"]')
        await asyncio.sleep(3)
        await page.screenshot(path="debug_screenshots/hf_after_login.png")
        print("   ✓ Screenshot: hf_after_login.png")
        print(f"   Current URL: {page.url}")

        # Step 4: Navigate to HuggingChat
        print("4. Navigating to HuggingChat...")
        await page.goto("https://huggingface.co/chat", timeout=60000)
        await asyncio.sleep(3)
        await page.screenshot(path="debug_screenshots/hc_loaded.png")
        print("   ✓ Screenshot: hc_loaded.png")
        print(f"   Current URL: {page.url}")

        # Step 5: Check for any modals/popups
        print("5. Checking for modals or welcome screens...")
        html = await page.content()
        with open("debug_screenshots/hc_page.html", "w") as f:
            f.write(html)
        print("   ✓ Saved page HTML to hc_page.html")

        # Step 6: Look for the chat interface
        print("6. Looking for chat interface...")
        
        # Find all buttons
        buttons = await page.query_selector_all('button')
        print(f"   Found {len(buttons)} buttons")
        
        # Find textareas
        textareas = await page.query_selector_all('textarea')
        print(f"   Found {len(textareas)} textareas")
        
        # Try to find the message input
        input_found = False
        for selector in ['textarea', '[contenteditable="true"]', 'input[type="text"]']:
            try:
                el = await page.wait_for_selector(selector, timeout=2000)
                if el:
                    print(f"   ✓ Found input: {selector}")
                    input_found = True
                    
                    # Try to type
                    print("7. Attempting to type message...")
                    await page.fill(selector, "Test message from debug")
                    await asyncio.sleep(1)
                    await page.screenshot(path="debug_screenshots/hc_typed.png")
                    print("   ✓ Screenshot: hc_typed.png")
                    
                    # Try to send
                    print("8. Sending message...")
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(5)
                    await page.screenshot(path="debug_screenshots/hc_after_send.png")
                    print("   ✓ Screenshot: hc_after_send.png")
                    
                    # Wait a bit more
                    await asyncio.sleep(5)
                    await page.screenshot(path="debug_screenshots/hc_response.png")
                    print("   ✓ Screenshot: hc_response.png")
                    break
            except Exception as e:
                print(f"   ✗ {selector}: {e}")

        if not input_found:
            print("   ❌ Could not find any input field!")
            
            # Check if we need to click "New chat" first
            try:
                new_chat = await page.query_selector('button:has-text("New chat")')
                if new_chat:
                    print("   Found 'New chat' button, clicking...")
                    await new_chat.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path="debug_screenshots/hc_after_newchat.png")
                    print("   ✓ Screenshot: hc_after_newchat.png")
            except Exception as e:
                print(f"   No 'New chat' button: {e}")

        await browser.close()
        print("\n✅ Debug complete! Check debug_screenshots/ folder.")


if __name__ == "__main__":
    asyncio.run(debug_with_screenshots())
