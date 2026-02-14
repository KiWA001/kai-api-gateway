"""
Test script for HuggingChat Provider
Run this to verify the HuggingChat browser automation works.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers.huggingchat_provider import HuggingChatProvider


async def test_huggingchat():
    """Test the HuggingChat provider."""
    print("🧪 Testing HuggingChat Provider...")
    print("-" * 50)

    provider = HuggingChatProvider()

    # Check if Playwright is available
    if not provider.is_available():
        print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    print("✅ Playwright is available")
    print(f"📋 Available models: {provider.get_available_models()}")
    print()

    # Test with default Omni router
    print("\n📝 Test 1: Using Omni router (default)")
    print("-" * 50)

    try:
        result = await provider.send_message("Say 'Hello from HuggingChat test' and nothing else.")
        print(f"✅ SUCCESS!")
        print(f"🤖 Model: {result['model']}")
        print(f"💬 Response: {result['response'][:200]}...")
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test with specific model
    print("\n📝 Test 2: Using Llama 3.3 70B")
    print("-" * 50)

    try:
        result = await provider.send_message(
            "What is 2+2? Answer with just the number.",
            model="meta-llama/Llama-3.3-70B-Instruct"
        )
        print(f"✅ SUCCESS!")
        print(f"🤖 Model: {result['model']}")
        print(f"💬 Response: {result['response'][:200]}...")
        print()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail completely if specific model doesn't work

    print("\n" + "=" * 50)
    print("🎉 HuggingChat tests completed!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_huggingchat())
    sys.exit(0 if success else 1)
