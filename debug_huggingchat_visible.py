"""
Debug script for HuggingChat - Visible browser to inspect page
"""

import asyncio
import os
from playwright.async_api import async_playwright

# Credentials
HF_USERNAME = "one@bo5.store"
HF_PASSWORD = "Zzzzz1$."


async def debug_huggingchat():
    """Launch visible browser to debug HuggingChat."""
    print("🔍 Launching visible browser to debug HuggingChat...")
    print("You can watch what's happening and interact if needed.")
    print("Press Ctrl+C to exit when done.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # VISIBLE browser
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )

        page = await context.new_page()

        # Step 1: Login
        print("Step 1: Logging in...")
        await page.goto("https://huggingface.co/login", timeout=60000)
        
        await page.fill('input[name="username"]', HF_USERNAME)
        await page.fill('input[name="password"]', HF_PASSWORD)
        await page.click('button[type="submit"]')
        
        # Wait for login to complete
        await page.wait_for_url(lambda url: "login" not in url, timeout=15000)
        print("✅ Logged in!")

        # Step 2: Navigate to HuggingChat
        print("\nStep 2: Navigating to HuggingChat...")
        await page.goto("https://huggingface.co/chat", timeout=60000)
        await asyncio.sleep(3)

        # Step 3: Inspect the page
        print("\nStep 3: Inspecting page structure...")
        
        # Find all buttons and their text
        buttons = await page.query_selector_all('button')
        print(f"Found {len(buttons)} buttons:")
        for i, btn in enumerate(buttons[:10]):  # First 10
            text = await btn.text_content()
            if text and text.strip():
                print(f"  {i}: {text.strip()[:50]}")

        # Find all textareas
        textareas = await page.query_selector_all('textarea')
        print(f"\nFound {len(textareas)} textareas")
        for i, ta in enumerate(textareas):
            placeholder = await ta.get_attribute('placeholder')
            print(f"  {i}: placeholder='{placeholder}'")

        # Find all inputs
        inputs = await page.query_selector_all('input')
        print(f"\nFound {len(inputs)} inputs")

        # Step 4: Try to find and click "New Chat" or similar
        print("\nStep 4: Looking for 'New chat' button...")
        try:
            new_chat = await page.wait_for_selector('button:has-text("New chat")', timeout=5000)
            if new_chat:
                print("Found 'New chat' button, clicking...")
                await new_chat.click()
                await asyncio.sleep(2)
        except:
            print("No 'New chat' button found (might already be in chat)")

        # Step 5: Find the message input
        print("\nStep 5: Finding message input...")
        
        # Try multiple selectors
        input_selectors = [
            'textarea[placeholder*="Ask"]',
            'textarea[placeholder*="Message"]',
            'textarea',
            '[contenteditable="true"]',
            'input[type="text"]',
        ]
        
        found_input = None
        for sel in input_selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=3000)
                if el:
                    print(f"✅ Found input: {sel}")
                    found_input = sel
                    break
            except:
                print(f"❌ Not found: {sel}")

        if found_input:
            # Step 6: Type a message
            print("\nStep 6: Typing test message...")
            await page.fill(found_input, "Say 'Test successful from debug script'")
            await asyncio.sleep(1)
            
            # Step 7: Send message
            print("Step 7: Sending message...")
            await page.keyboard.press("Enter")
            
            # Step 8: Wait and watch for response
            print("\nStep 8: Waiting for response (30 seconds)...")
            print("Watch the browser window to see what happens!\n")
            
            for i in range(30):
                await asyncio.sleep(1)
                if i % 5 == 0:
                    # Try to extract any response text
                    try:
                        messages = await page.evaluate("""
                            () => {
                                const msgs = document.querySelectorAll('[data-message-author-role="assistant"], .assistant-message, [class*="assistant"], article');
                                return Array.from(msgs).map(m => m.innerText || m.textContent).slice(-1);
                            }
                        """)
                        if messages and messages[0]:
                            print(f"Second {i}: Response preview: {messages[0][:100]}...")
                    except:
                        pass
        else:
            print("❌ Could not find any input field!")

        print("\n⏳ Keeping browser open for 60 seconds...")
        print("You can manually inspect the page now.")
        print("Press Ctrl+C to close.\n")
        
        try:
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            pass

        await browser.close()
        print("✅ Debug session complete.")


if __name__ == "__main__":
    asyncio.run(debug_huggingchat())
