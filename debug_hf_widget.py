#!/usr/bin/env python3
"""
Debug script to inspect Hugging Face model page widget structure
"""

import asyncio
from playwright.async_api import async_playwright

HF_USERNAME = "one@bo5.store"
HF_PASSWORD = "Zzzzz1$."

async def inspect_widget():
    """Navigate to a model page and inspect the widget HTML structure."""
    print("🔍 Inspecting HF Model Widget Structure...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        page = await context.new_page()
        
        # Navigate to a model page with widget
        model_url = "https://huggingface.co/moonshotai/Kimi-K2.5"
        print(f"1. Navigating to {model_url}...")
        await page.goto(model_url, timeout=60000)
        await asyncio.sleep(3)
        
        # Check if login is needed
        login_btn = await page.query_selector('a[href*="login"], button:has-text("Log in")')
        if login_btn:
            print("2. Login required, logging in...")
            await page.goto("https://huggingface.co/login", timeout=30000)
            await page.fill('input[name="username"]', HF_USERNAME)
            await page.fill('input[name="password"]', HF_PASSWORD)
            await page.click('button[type="submit"]')
            await asyncio.sleep(3)
            await page.goto(model_url, timeout=30000)
            await asyncio.sleep(3)
        else:
            print("2. Already logged in")
        
        # Accept cookies if present
        try:
            cookie_btn = await page.wait_for_selector('button:has-text("Accept all")', timeout=3000)
            if cookie_btn:
                await cookie_btn.click()
                await asyncio.sleep(1)
                print("3. Accepted cookies")
        except:
            print("3. No cookie banner")
        
        # Scroll down to find the widget
        print("4. Scrolling to find widget...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
        await asyncio.sleep(2)
        
        # Take screenshot
        await page.screenshot(path="/tmp/hf_widget_debug.png", full_page=False)
        print("5. Screenshot saved to /tmp/hf_widget_debug.png")
        
        # Inspect the page structure
        print("\n📋 Analyzing page structure...\n")
        
        # Look for widget containers
        widgets = await page.query_selector_all('[class*="widget"], [class*="inference"], [data-target*="Widget"]')
        print(f"Found {len(widgets)} potential widget elements")
        
        # Get HTML structure around the widget area
        page_structure = await page.evaluate("""
            () => {
                const results = {
                    iframes: document.querySelectorAll('iframe').length,
                    textareas: [],
                    inputs: [],
                    chatContainers: [],
                    allWidgets: []
                };
                
                // Find all textareas
                document.querySelectorAll('textarea').forEach((el, i) => {
                    results.textareas.push({
                        index: i,
                        placeholder: el.placeholder,
                        className: el.className,
                        id: el.id,
                        parentClass: el.parentElement?.className?.substring(0, 100)
                    });
                });
                
                // Find elements with 'chat' or 'message' in class
                document.querySelectorAll('[class*="chat" i], [class*="message" i]').forEach((el, i) => {
                    if (i < 10) {  // Limit output
                        results.chatContainers.push({
                            tag: el.tagName,
                            className: el.className,
                            text: el.textContent?.substring(0, 100)
                        });
                    }
                });
                
                // Find all elements with 'widget' in class or data attributes
                document.querySelectorAll('[class*="widget" i], [data-target*="Widget" i], [class*="inference" i]').forEach((el, i) => {
                    if (i < 10) {
                        results.allWidgets.push({
                            tag: el.tagName,
                            className: el.className?.substring(0, 200),
                            dataTarget: el.getAttribute('data-target'),
                            innerHTML: el.innerHTML?.substring(0, 500)
                        });
                    }
                });
                
                return results;
            }
        """)
        
        print("\n--- TEXTAREAS ---")
        for ta in page_structure['textareas']:
            print(f"  [{ta['index']}] Placeholder: '{ta['placeholder']}'")
            print(f"      Class: {ta['className']}")
            print(f"      Parent: {ta['parentClass']}")
            print()
        
        print("\n--- CHAT/MESSAGE ELEMENTS ---")
        for el in page_structure['chatContainers']:
            print(f"  Tag: {el['tag']}")
            print(f"  Class: {el['className']}")
            print(f"  Text: {el['text']}")
            print()
        
        print("\n--- WIDGET ELEMENTS ---")
        for el in page_structure['allWidgets']:
            print(f"  Tag: {el['tag']}")
            print(f"  Class: {el['className']}")
            print(f"  Data-target: {el['dataTarget']}")
            print(f"  HTML Preview: {el['innerHTML']}")
            print()
        
        print(f"\n--- IFRAMES ---")
        print(f"Found {page_structure['iframes']} iframes on page")
        
        # Try to find and interact with input
        print("\n🎯 Attempting to find chat input...")
        input_found = False
        
        # Try common selectors
        selectors = [
            'textarea[placeholder*="chat" i]',
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="ask" i]',
            '[class*="chat"] textarea',
            '[class*="widget"] textarea',
            '[data-target*="Chat"] textarea',
            '[contenteditable="true"]',
        ]
        
        for sel in selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=2000)
                if el:
                    print(f"✅ Found input with selector: {sel}")
                    input_found = True
                    
                    # Try to type a test message
                    await el.fill("Hello, this is a test")
                    await asyncio.sleep(1)
                    print("✅ Typed test message")
                    
                    # Look for send button
                    send_btn = await page.query_selector('button[type="submit"], button:has-text("Send"), [class*="send"]')
                    if send_btn:
                        print("✅ Found send button")
                    else:
                        print("⚠️ No send button found, trying Enter key...")
                        await page.keyboard.press("Enter")
                    
                    break
            except Exception as e:
                print(f"❌ Selector failed: {sel} - {e}")
        
        if not input_found:
            print("❌ Could not find chat input with any selector")
        
        print("\n⏳ Waiting 10 seconds so you can inspect the browser...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("\n✅ Debug complete!")

if __name__ == "__main__":
    asyncio.run(inspect_widget())
