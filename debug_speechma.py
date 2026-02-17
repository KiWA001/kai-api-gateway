#!/usr/bin/env python3
"""
Debug script to inspect SpeechMA CAPTCHA
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_captcha():
    """Debug the SpeechMA page to see CAPTCHA structure."""
    print("🔍 Debugging SpeechMA CAPTCHA...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        print("1. Navigating to SpeechMA...")
        await page.goto("https://speechma.com", wait_until='networkidle', timeout=60000)
        await asyncio.sleep(3)
        
        print("2. Taking screenshot...")
        await page.screenshot(path="/tmp/speechma_debug.png", full_page=True)
        print("   Screenshot saved to /tmp/speechma_debug.png")
        
        print("\n3. Analyzing page structure...")
        
        # Look for CAPTCHA elements
        captcha_info = await page.evaluate("""
            () => {
                const result = {
                    images: [],
                    inputs: [],
                    textareas: [],
                    buttons: [],
                    captcha_elements: []
                };
                
                // Find all images
                document.querySelectorAll('img').forEach((img, i) => {
                    result.images.push({
                        index: i,
                        src: img.src?.substring(0, 100),
                        alt: img.alt,
                        class: img.className
                    });
                });
                
                // Find all inputs
                document.querySelectorAll('input').forEach((input, i) => {
                    result.inputs.push({
                        index: i,
                        type: input.type,
                        name: input.name,
                        placeholder: input.placeholder,
                        class: input.className,
                        id: input.id
                    });
                });
                
                // Find all textareas
                document.querySelectorAll('textarea').forEach((ta, i) => {
                    result.textareas.push({
                        index: i,
                        placeholder: ta.placeholder,
                        class: ta.className,
                        id: ta.id
                    });
                });
                
                // Find buttons
                document.querySelectorAll('button').forEach((btn, i) => {
                    if (i < 10) {
                        result.buttons.push({
                            index: i,
                            text: btn.textContent?.substring(0, 50),
                            class: btn.className,
                            onclick: btn.getAttribute('onclick')?.substring(0, 100)
                        });
                    }
                });
                
                // Look for elements with 'captcha' in class or id
                document.querySelectorAll('[class*="captcha" i], [id*="captcha" i]').forEach((el, i) => {
                    result.captcha_elements.push({
                        tag: el.tagName,
                        class: el.className,
                        id: el.id,
                        innerHTML: el.innerHTML?.substring(0, 200)
                    });
                });
                
                return result;
            }
        """)
        
        print("\n--- IMAGES ---")
        for img in captcha_info['images']:
            print(f"  [{img['index']}] src: {img['src']}, alt: '{img['alt']}', class: {img['class']}")
        
        print("\n--- INPUTS ---")
        for inp in captcha_info['inputs']:
            print(f"  [{inp['index']}] type: {inp['type']}, name: {inp['name']}, placeholder: '{inp['placeholder']}', class: {inp['class']}, id: {inp['id']}")
        
        print("\n--- TEXTAREAS ---")
        for ta in captcha_info['textareas']:
            print(f"  [{ta['index']}] placeholder: '{ta['placeholder']}', class: {ta['class']}, id: {ta['id']}")
        
        print("\n--- BUTTONS ---")
        for btn in captcha_info['buttons']:
            print(f"  [{btn['index']}] text: '{btn['text']}', class: {btn['class']}, onclick: {btn['onclick']}")
        
        print("\n--- CAPTCHA ELEMENTS ---")
        for el in captcha_info['captcha_elements']:
            print(f"  Tag: {el['tag']}, class: {el['class']}, id: {el['id']}")
            print(f"  HTML: {el['innerHTML']}")
        
        print("\n4. Waiting 10 seconds for you to inspect...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("\n✅ Debug complete!")

if __name__ == "__main__":
    asyncio.run(debug_captcha())
