"""
Test script for Microsoft Copilot Provider
Run this to verify the Copilot browser automation works.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers.copilot_provider import CopilotProvider


async def test_copilot():
    """Test the Copilot provider."""
    print("🧪 Testing Microsoft Copilot Provider...")
    print("-" * 50)

    provider = CopilotProvider()

    # Check if Playwright is available
    if not provider.is_available():
        print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    print("✅ Playwright is available")
    print(f"📋 Available models: {provider.get_available_models()}")
    print()

    # Test prompts
    test_prompts = [
        "Say 'Hello from Copilot test' and nothing else.",
        "What is 2+2? Answer with just the number.",
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📝 Test {i}: {prompt[:50]}...")
        print("-" * 50)

        try:
            result = await provider.send_message(prompt)
            print(f"✅ SUCCESS!")
            print(f"🤖 Model: {result['model']}")
            print(f"💬 Response: {result['response'][:200]}...")
            print()
        except Exception as e:
            print(f"❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n" + "=" * 50)
    print("🎉 All Copilot tests passed!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_copilot())
    sys.exit(0 if success else 1)
