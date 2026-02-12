
import asyncio
from providers.g4f_provider import G4FProvider

async def test_g4f():
    print("Testing G4F Provider...")
    provider = G4FProvider()
    
    # Test 1: Simple Hello with gpt-4o-mini
    print("\n--- Test gpt-4o-mini ---")
    try:
        res = await provider.send_message("Hello, are you working?", model="gpt-4o-mini")
        print(f"Response: {res}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: gpt-4
    print("\n--- Test gpt-4 ---")
    try:
        res = await provider.send_message("Hello", model="gpt-4")
        print(f"Response: {res}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_g4f())
