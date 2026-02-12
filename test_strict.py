
import asyncio
import sys
# Fake logger to avoid errors
import logging
logging.basicConfig(level=logging.ERROR)

from engine import AIEngine

async def test_strict():
    print("=== Testing Strict Mode via Engine ===")
    engine = AIEngine()
    
    # 1. Test Valid Strict Request (gpt-4o-mini via g4f)
    print("\n1. Valid Strict Request (g4f / gpt-4o-mini)...")
    try:
        res = await engine.chat("Hi", model="gpt-4o-mini", provider="g4f")
        print("✅ Success:", res['model'], res['provider'])
    except Exception as e:
        print("❌ Unexpected Error:", e)

    # 1.5 Test Valid Strict Request (Pollinations / gpt-oss-20b)
    print("\n1.5 Valid Strict Request (pollinations / gpt-oss-20b)...")
    try:
        res = await engine.chat("Hi", model="gpt-oss-20b", provider="pollinations")
        print("✅ Success:", res['model'], res['provider'])
    except Exception as e:
        print("❌ Unexpected Error:", e)

    # 2. Test Invalid Provider
    print("\n2. Invalid Provider (invalid_prov)...")
    try:
        await engine.chat("Hi", provider="invalid_prov")
        print("❌ Failed: Should have raised error")
    except ValueError as e:
        print("✅ Caught Expected Error:", e)
    except Exception as e:
        print("❌ Wrong Error:", type(e), e)

    # 3. Test Invalid Model
    print("\n3. Invalid Model (xyz-123)...")
    try:
        await engine.chat("Hi", model="xyz-123")
        print("❌ Failed: Should have raised error")
    except ValueError as e:
        print("✅ Caught Expected Error:", e)
    except Exception as e:
        print("❌ Wrong Error:", type(e), e)

    # 4. Test Valid Model, Invalid Provider for that model
    # e.g. 'gpt-oss-20b' is pollination only. Try with g4f.
    print("\n4. Model Mismatch (gpt-oss-20b on g4f)...")
    try:
        await engine.chat("Hi", model="gpt-oss-20b", provider="g4f")
        print("❌ Failed: Should have raised error")
    except ValueError as e:
        print("✅ Caught Expected Error:", e)
    except Exception as e:
        print("❌ Wrong Error:", type(e), e)
        
    # 5. Test Auto (Should still work)
    print("\n5. Auto Mode...")
    try:
        res = await engine.chat("Hi", provider="auto", model="gpt-4o-mini") # Specific model, auto provider
        print("✅ Success (Auto Prov):", res['model'], res['provider'])
    except Exception as e:
        print("❌ Error in Auto:", e)

    # 6. Model Only Strict (Success Case)
    print("\n6. Model Only Strict (gpt-oss-20b, provider=auto)...")
    try:
        res = await engine.chat("Hi", model="gpt-oss-20b", provider="auto")
        print("✅ Success:", res['model'], res['provider'])
    except Exception as e:
        print("❌ Unexpected Error:", e)

if __name__ == "__main__":
    asyncio.run(test_strict())
