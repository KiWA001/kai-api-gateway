import asyncio
from providers.zai_provider import ZaiProvider

async def main():
    z = ZaiProvider()
    print("Testing Z.ai...")
    try:
        res = await z.send_message("Hello")
        print(res)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
