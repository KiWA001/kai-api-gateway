#!/usr/bin/env python3
"""
Local Test for HuggingFace Widget Provider
Run this to verify the provider works before pushing to git.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/mac/KAI_API')

from providers.huggingface_widget_provider import HuggingFaceWidgetProvider

async def test_provider():
    """Test the HF Widget provider locally."""
    print("🧪 Testing HuggingFace Widget Provider...\n")
    
    provider = HuggingFaceWidgetProvider()
    
    # Test 1: Check if available
    print("1. Checking if Playwright is available...")
    if not provider.is_available():
        print("❌ Playwright not installed!")
        print("Run: pip install playwright && playwright install chromium")
        return
    print("✅ Playwright is available\n")
    
    # Test 2: List models
    print("2. Available models:")
    models = provider.get_available_models()
    for i, model in enumerate(models[:5], 1):
        print(f"   {i}. {model}")
    print(f"   ... and {len(models) - 5} more\n")
    
    # Test 3: Send a test message
    print("3. Testing with Kimi-K2.5...")
    print("   (This will open a browser and test the widget)")
    print("   Press Ctrl+C to cancel if you don't want to test now\n")
    
    try:
        result = await provider.send_message(
            prompt="Say 'Hello from HF Widget test' and nothing else.",
            model="hf-kimi-k2.5"
        )
        
        print("✅ SUCCESS!")
        print(f"\nResponse:\n{result['response']}\n")
        print(f"Model used: {result['model']}")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_provider())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test cancelled by user")
