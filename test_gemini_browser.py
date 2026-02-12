"""
Gemini Browser Test
===================
Tests the Gemini Playwright integration.
"""
import time
from playwright.sync_api import sync_playwright

def test_gemini_browser():
    print("=== Gemini Browser Test ===\n")

    with sync_playwright() as p:
        print("Launching browser...")
        # Headless=False to see what's happening during debug
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = context.new_page()

        print("[1] Loading https://gemini.google.com/ ...")
        page.goto("https://gemini.google.com/", timeout=60000)
        
        # Debug: Wait and see
        time.sleep(5)
        
        print("[2] Finding input...")
        # Try generic selectors
        textarea = None
        selectors = [
             'div[contenteditable="true"]',
             'div[role="textbox"]',
             'rich-textarea'
        ]
        
        for sel in selectors:
            try:
                textarea = page.wait_for_selector(sel, timeout=5000)
                if textarea:
                    print(f"    ✅ Found input with selector: {sel}")
                    break
            except:
                pass
                
        if not textarea:
            print("    ❌ Could not find input area. Dumping page...")
            page.screenshot(path="gemini_fail.png")
            return

        test_prompt = "Hello ..... answer in plain text"
        print(f"\n[3] Sending: '{test_prompt}'")
        
        textarea.click()
        page.keyboard.type(test_prompt, delay=30)
        time.sleep(1)
        page.keyboard.press("Enter")
        
        print("\n[4] Waiting for response...")
        time.sleep(15) 
        
        # Scrape
        response_text = page.evaluate("""
            () => {
               const all = document.querySelectorAll('*');
               // Basic heuristic: look for large blocks of text that appeared recently
               // But let's try specific Gemini selectors first
               
               const candidates = document.querySelectorAll('model-response');
               if (candidates.length > 0) {
                   return candidates[candidates.length - 1].innerText;
               }
               
               // Fallback: look for generic message containers
               // 'message-content' often used
               
               return document.body.innerText.slice(0, 500); // debug fallback
            }
        """)
        
        print(f"\n=== RESPONSE ===\n{response_text}\n================")
        
        # Keep open briefly
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    test_gemini_browser()
