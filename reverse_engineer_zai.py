"""
Z.ai curl_cffi Test - Using EXACT browser headers discovered via Playwright
Key findings:
  - Header: x-fe-version: prod-fe-1.0.237
  - Header: x-signature: <hash of message>
  - URL query params: timestamp, requestId, user_id, version, platform, token, browser fingerprint
"""
from curl_cffi import requests
import json
import uuid
import hashlib
import time
from datetime import datetime, timezone

BASE = "https://chat.z.ai"


def generate_signature(prompt):
    """Generate x-signature hash. Need to figure out the algorithm."""
    # The captured signature was: 45f5ed8787e9ae757ea508e03259661b40e08acc189430a6f0f3869a2ac546d1
    # For message "Say hi" — this is a SHA-256 hash of something
    # Let's try various combinations
    candidates = [
        prompt,
        f"Say hi",
        prompt.lower(),
    ]
    for c in candidates:
        h = hashlib.sha256(c.encode()).hexdigest()
        print(f"  sha256('{c}') = {h}")
    
    # For now, just use sha256 of the prompt
    return hashlib.sha256(prompt.encode()).hexdigest()


def test_zai():
    print("=== Z.ai curl_cffi with Real Browser Headers ===\n")
    
    s = requests.Session(impersonate="chrome120")
    
    # Step 1: Get token
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://chat.z.ai",
        "Referer": "https://chat.z.ai/",
    }
    r = s.get(f"{BASE}/api/v1/auths/", headers=headers)
    data = r.json()
    token = data["token"]
    user_id = data.get("id", str(uuid.uuid4()))
    print(f"Token: {token[:20]}...")
    print(f"User ID: {user_id}")
    
    # Step 2: Create a chat
    chat_pay = {"chat": {"title": "Test", "models": ["glm-4-flash"], "tags": []}}
    r = s.post(f"{BASE}/api/v1/chats/new", headers={**headers, "Authorization": f"Bearer {token}"}, json=chat_pay, timeout=5)
    chat_id = r.json()["id"]
    print(f"Chat ID: {chat_id}")
    
    # Step 3: Build the EXACT request the browser makes
    prompt = "Say hello in one word"
    now = datetime.now(timezone.utc)
    timestamp = int(time.time() * 1000)
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    user_message_id = str(uuid.uuid4())
    
    # Build query params (exactly as the browser sends them)
    query_params = {
        "timestamp": str(timestamp),
        "requestId": request_id,
        "user_id": user_id,
        "version": "0.0.1",
        "platform": "web",
        "token": token,
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "language": "en-US",
        "languages": "en-US",
        "timezone": "America/New_York",
        "cookie_enabled": "true",
        "screen_width": "1280",
        "screen_height": "720",
        "screen_resolution": "1280x720",
        "viewport_height": "720",
        "viewport_width": "1280",
        "viewport_size": "1280x720",
        "color_depth": "24",
        "pixel_ratio": "1",
        "current_url": f"https://chat.z.ai/c/{chat_id}",
        "pathname": f"/c/{chat_id}",
        "search": "",
        "hash": "",
        "host": "chat.z.ai",
        "hostname": "chat.z.ai",
        "protocol": "https:",
        "referrer": "",
        "title": "Z.ai - Free AI Chatbot & Agent powered by GLM-5 & GLM-4.7",
        "timezone_offset": "-300",
        "local_time": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "utc_time": now.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "is_mobile": "false",
        "is_touch": "false",
        "max_touch_points": "0",
        "browser_name": "Chrome",
        "os_name": "Mac OS",
        "signature_timestamp": str(timestamp),
    }
    
    # Headers (exactly as browser sends)
    req_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Origin": "https://chat.z.ai",
        "Referer": f"https://chat.z.ai/c/{chat_id}",
        "x-fe-version": "prod-fe-1.0.237",
        "x-signature": generate_signature(prompt),
    }
    
    # Body (exactly as browser sends)
    body = {
        "stream": True,
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "signature_prompt": prompt,
        "params": {},
        "extra": {},
        "features": {
            "image_generation": False,
            "web_search": False,
            "auto_web_search": False,
            "preview_mode": True,
            "flags": [],
            "enable_thinking": False,
        },
        "variables": {
            "{{USER_NAME}}": "Guest",
            "{{USER_LOCATION}}": "Unknown",
            "{{CURRENT_DATETIME}}": now.strftime("%Y-%m-%d %H:%M:%S"),
            "{{CURRENT_DATE}}": now.strftime("%Y-%m-%d"),
            "{{CURRENT_TIME}}": now.strftime("%H:%M:%S"),
            "{{CURRENT_WEEKDAY}}": now.strftime("%A"),
            "{{CURRENT_TIMEZONE}}": "America/New_York",
            "{{USER_LANGUAGE}}": "en-US",
        },
        "chat_id": chat_id,
        "id": message_id,
        "current_user_message_id": user_message_id,
        "current_user_message_parent_id": None,
        "background_tasks": {
            "title_generation": True,
            "tags_generation": True,
        },
    }
    
    # Build URL with query params
    from urllib.parse import urlencode
    url = f"{BASE}/api/v2/chat/completions?{urlencode(query_params)}"
    
    print(f"\n--- Sending chat request ---")
    print(f"URL length: {len(url)}")
    
    r = s.post(url, headers=req_headers, json=body, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Response (first 1000 chars):")
    print(r.text[:1000])


if __name__ == "__main__":
    test_zai()
