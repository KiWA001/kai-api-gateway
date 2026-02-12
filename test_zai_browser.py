"""
Z.ai Browser v11 - Chromium-based Chat Client
===============================================
Uses Playwright Chromium to interact with https://chat.z.ai/

Strategy:
1. Launch Chromium, navigate to chat.z.ai
2. Wait for page to hydrate (textarea appears)
3. Type a message and press Enter
4. Capture the network request details (URL, headers, body) for reverse engineering
5. Wait for the AI response to appear in the DOM
6. Scrape the response text from the page
"""
import json
import time
import sys
from playwright.sync_api import sync_playwright


def test_zai_browser():
    print("=== Z.ai Browser v11 (DOM Scraping + Network Capture) ===\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
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

        # ──────────────────────────────────────────────
        # Capture ALL network requests to the chat API
        # ──────────────────────────────────────────────
        captured_requests = []

        def on_request(request):
            if "chat/completions" in request.url:
                print(f"\n    🔍 CAPTURED REQUEST:")
                print(f"       URL: {request.url[:200]}...")
                print(f"       Method: {request.method}")
                
                headers = dict(request.headers)
                print(f"       Headers:")
                for k, v in headers.items():
                    if k.lower() in ["authorization", "x-signature", "x-fe-version", "content-type", "origin", "referer"]:
                        display_v = v[:80] + "..." if len(v) > 80 else v
                        print(f"         {k}: {display_v}")
                
                post_data = request.post_data
                if post_data:
                    try:
                        body = json.loads(post_data)
                        print(f"       Body keys: {list(body.keys())}")
                        print(f"       Model: {body.get('model', 'N/A')}")
                        print(f"       Stream: {body.get('stream', 'N/A')}")
                    except:
                        print(f"       Raw body: {post_data[:200]}")
                
                captured_requests.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": headers,
                    "post_data": post_data,
                })

        page.on("request", on_request)

        # ──────────────────────────────────────────────
        # Step 1: Load and hydrate
        # ──────────────────────────────────────────────
        print("[1] Loading https://chat.z.ai/ ...")
        page.goto("https://chat.z.ai/", timeout=120000)
        page.wait_for_selector("textarea", timeout=120000)
        print("    ✅ Page loaded, textarea found!")
        time.sleep(3)  # Let JavaScript fully hydrate

        # ──────────────────────────────────────────────
        # Step 2: Send a test message
        # ──────────────────────────────────────────────
        test_prompt = "Say hello in exactly one word, nothing else"
        print(f"\n[2] Sending: '{test_prompt}'")
        
        textarea = page.query_selector("textarea")
        textarea.click()
        page.keyboard.type(test_prompt, delay=30)
        time.sleep(0.5)
        page.keyboard.press("Enter")
        print("    ✅ Message sent!")

        # ──────────────────────────────────────────────
        # Step 3: Wait for AI response to appear in DOM
        # ──────────────────────────────────────────────
        print("\n[3] Waiting for AI response in DOM...")
        
        # Wait up to 30 seconds for a response to appear
        max_wait = 30
        response_text = ""
        for i in range(max_wait):
            time.sleep(1)
            
            # Try to find response elements - Z.ai uses markdown rendering
            # Look for assistant message containers
            response_text = page.evaluate("""
                () => {
                    // Try various selectors that Z.ai might use for responses
                    const selectors = [
                        '[data-message-role="assistant"]',
                        '.assistant-message',
                        '.message-content',
                        '.prose',
                        '.markdown-body',
                        '[class*="assistant"]',
                        '[class*="response"]',
                        '[class*="bot-message"]',
                        // Generic: find all chat bubbles that aren't the user's
                        '.chat-message:last-child',
                    ];
                    
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {
                            const last = els[els.length - 1];
                            const text = last.innerText || last.textContent || '';
                            if (text.trim().length > 0) {
                                return `[${sel}] ${text.trim()}`;
                            }
                        }
                    }
                    
                    // Fallback: get ALL text content and look for new text
                    return '';
                }
            """)
            
            if response_text:
                print(f"    ✅ Got response after {i+1}s")
                break
            
            # Also check if we can see any message containers at all
            if i == 10:
                # Debug: dump the page structure
                debug = page.evaluate("""
                    () => {
                        const all = document.querySelectorAll('*');
                        const classes = new Set();
                        for (const el of all) {
                            if (el.className && typeof el.className === 'string') {
                                el.className.split(' ').forEach(c => {
                                    if (c.includes('message') || c.includes('chat') || c.includes('prose') || 
                                        c.includes('assistant') || c.includes('response') || c.includes('markdown')) {
                                        classes.add(c);
                                    }
                                });
                            }
                        }
                        return Array.from(classes).slice(0, 30);
                    }
                """)
                print(f"    🔎 Relevant CSS classes found: {debug}")
            
            if i % 5 == 4:
                print(f"    ⏳ Still waiting... ({i+1}s)")
        
        if not response_text:
            # Last resort: take a screenshot and dump body text
            print("    ⚠️ No response found via selectors. Dumping page state...")
            page.screenshot(path="/Users/mac/KAI_API/zai_debug.png")
            print("    📸 Screenshot saved to zai_debug.png")
            
            body_text = page.evaluate("() => document.body.innerText")
            print(f"    📄 Body text (first 500 chars):\n{body_text[:500]}")
        else:
            print(f"\n    === AI RESPONSE ===")
            print(f"    {response_text}")
            print(f"    ==================")

        # ──────────────────────────────────────────────
        # Step 4: Dump captured request details for reverse engineering
        # ──────────────────────────────────────────────
        print(f"\n[4] Network capture summary:")
        print(f"    Total API requests captured: {len(captured_requests)}")
        
        if captured_requests:
            req = captured_requests[0]
            print(f"\n    === FIRST CAPTURED REQUEST (for reverse engineering) ===")
            print(f"    Full URL: {req['url']}")
            print(f"\n    All headers:")
            for k, v in req["headers"].items():
                print(f"      {k}: {v[:120]}")
            if req.get("post_data"):
                try:
                    body = json.loads(req["post_data"])
                    print(f"\n    Full body (JSON):")
                    print(json.dumps(body, indent=2)[:2000])
                except:
                    print(f"\n    Raw body: {req['post_data'][:500]}")
            
            # Save captured data for analysis
            with open("/Users/mac/KAI_API/zai_captured.json", "w") as f:
                json.dump(captured_requests, f, indent=2, default=str)
            print(f"\n    💾 Full capture saved to zai_captured.json")

        # ──────────────────────────────────────────────
        # Step 5: Test second message (session reuse)
        # ──────────────────────────────────────────────
        print(f"\n[5] Testing session reuse with second message...")
        
        textarea = page.wait_for_selector("textarea", timeout=10000)
        textarea.click()
        page.keyboard.type("What is 2+2?", delay=30)
        time.sleep(0.3)
        page.keyboard.press("Enter")
        
        # Wait for response
        time.sleep(15)
        
        response2 = page.evaluate("""
            () => {
                // Get the last prose/message element
                const selectors = [
                    '.prose',
                    '[data-message-role="assistant"]',
                    '[class*="assistant"]',
                    '.message-content',
                    '.markdown-body',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 1) {  // Should be at least 2 responses now
                        const last = els[els.length - 1];
                        return last.innerText || last.textContent || '';
                    }
                }
                return '';
            }
        """)
        print(f"    2nd Response: '{response2.strip()[:200]}'")

        browser.close()
        print(f"\n{'='*60}")
        print(f"=== DONE ===")
        print(f"{'='*60}")


if __name__ == "__main__":
    test_zai_browser()
