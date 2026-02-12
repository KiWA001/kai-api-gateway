import asyncio
import logging
import sys
import time

# Mocking config and engine for standalone execution if needed, 
# or importing if they exist and are compatible.
# We will try to import first.
sys.path.append('.')

try:
    from engine import AIEngine
    from config import MODEL_RANKING
except ImportError:
    print("Could not import engine/config. Please run from the root directory.")
    sys.exit(1)

logging.basicConfig(level=logging.WARNING)

# Extended list of models to test
NEW_CANDIDATES = [
    # Pollinations
    ("bidara", "pollinations", "bidara"),
    ("chickytutor", "pollinations", "chickytutor"),
    ("midijourney", "pollinations", "midijourney"),
    ("searchgpt", "pollinations", "searchgpt"),
    ("evil", "pollinations", "evil"),
    ("p1", "pollinations", "p1"),
    
    # G4F - Hypothetical/New
    ("deepseek-r1", "g4f", "deepseek-r1"),
    ("o3-mini", "g4f", "o3-mini"),
    ("gpt-4-turbo", "g4f", "gpt-4-turbo"),
]

# Combine existing ranking with new candidates
FULL_TEST_LIST = MODEL_RANKING + NEW_CANDIDATES

async def test_access():
    print(f'=== K-AI API Browser Access Test (Extended) ===')
    engine = AIEngine()
    results = []
    
    print(f'\n[Testing {len(FULL_TEST_LIST)} models...]')
    
    # We want to test them in parallel to save time, but the engine might not support concurrent usage 
    # if it shares state. We'll do sequential for safety as per original script.
    
    for fn, pn, pid in FULL_TEST_LIST:
        prov = engine.get_provider(pn)
        if not prov:
            results.append((fn, 'SKIP', 'Provider missing'))
            print(f'  ⚠️ {fn} ({pn}) skipped: Provider missing')
            continue
            
        print(f'  Testing {fn} ({pid})...', end='\r')
        try:
            # We want to see if they accept a browser-like request
            # Using a simple "Hello" to check liveness
            r = await prov.send_message('Hello', model=pid)
            if not r.get('response'): 
                raise ValueError('Empty response')
            results.append((fn, 'PASS', 'OK'))
            print(f'  ✅ {fn} ({pn}) accepted browser request')
        except Exception as e:
            error_msg = str(e)[:100]
            results.append((fn, 'FAIL', error_msg))
            print(f'  ❌ {fn} ({pn}) rejected: {error_msg}')

    # Check Minimum Count
    working = [r for r in results if r[1] == 'PASS']
    working_count = len(working)
    total = len(results)
    
    print('\n=== Status Report ===')
    print(f'Total Tested: {total}')
    print(f'Working: {working_count}')
    
    print('\n=== Working Models ===')
    for w in working:
        print(f'- {w[0]}')

    if working_count < 10:
        print('\n⚠️ CRITICAL: Working models < 10! Do NOT delete any, even broken ones.')
    else:
        print('\n✅ Model count sufficient.')

if __name__ == "__main__":
    asyncio.run(test_access())
