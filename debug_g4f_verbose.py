
import asyncio
import os
import sys

# Simulate Vercel Environment
os.environ["HOME"] = "/tmp"

try:
    import g4f
    from g4f.client import Client
except ImportError:
    print("g4f not installed")
    sys.exit(1)

# Enable debug logging
g4f.debug.logging = True

async def test_g4f_verbose():
    print("=== Debugging G4F Provider Selection ===")
    
    models = ["gpt-4o-mini", "gpt-4"]
    
    for model in models:
        print(f"\n--- Testing {model} ---")
        try:
            client = Client()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello, are you working?"}],
            )
            print(f"✅ Success! Response: {response.choices[0].message.content[:50]}...")
            print(f"   Provider used: {response.provider}")
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_g4f_verbose())
