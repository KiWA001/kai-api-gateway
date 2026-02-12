import asyncio
from engine import AIEngine
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Initializing Engine ---")
    engine = AIEngine()
    
    print("\n--- Checking Stats ---")
    stats = engine.get_stats()
    print(f"Stats Count: {len(stats)}")
    print(stats)
    
    if not stats:
        print("\nStats are EMPTY. This explains the 'deserted' dashboard.")
        print("Running a quick test to generate data...")
        await engine.test_all_models()
        print("\n--- Re-checking Stats ---")
        stats = engine.get_stats()
        print(f"Stats Count: {len(stats)}")
        print(stats)

if __name__ == "__main__":
    asyncio.run(main())
