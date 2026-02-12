
import asyncio
from engine import AIEngine
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("Initializing Engine...")
    engine = AIEngine()
    print("Clearing Stats...")
    engine.clear_stats()
    print("Done!")

if __name__ == "__main__":
    main()
