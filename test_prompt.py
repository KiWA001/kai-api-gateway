
import asyncio
import os
import logging
from engine import AIEngine

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    print("Initializing Engine...")
    engine = AIEngine()
    
    # Mocking system prompt file if it doesn't exist (it should)
    
    print("\n--- Testing Chat ---")
    try:
        # We try 'opencode' because we know we settled auth for it, 
        # OR we try 'g4f'/pollinations if they are easier.
        # User reported issue on 'gemini-3-flash'.
        # Let's try to mock the provider response handling to see what PROMPT it actually gets?
        # Actually, we can just print the prompt in engine.py by adding a log.
        
        # But let's run a real request if possible.
        # If not, at least we see if it crashes.
        
        response = await engine.chat(
            prompt="Hello! Are you there?",
            model="gemini", # Friendly name for gemini-pro or similar, mapped in config
            provider="auto"
        )
        print(f"\nResponse: {response['response']}")
        print(f"Model used: {response['model']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
