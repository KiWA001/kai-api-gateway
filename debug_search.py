import logging
import sys
from search_engine import SearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    print("--- Initializing SearchEngine ---")
    se = SearchEngine()
    
    # Test 1: Simple Search
    query = "python async await tutorial"
    print(f"\n--- Testing Simple Search: '{query}' ---")
    results = se.simple_search(query, max_results=3)
    
    if results:
        print(f"Success! Found {len(results)} results.")
        for i, r in enumerate(results):
            print(f"[{i+1}] {r.get('title', 'No Title')}")
            print(f"    {r.get('href', 'No URL')}")
            print(f"    {r.get('body', '')[:100]}...")
    else:
        print("FAILURE: No results found.")

    # Test 2: Another Query
    query2 = "best pizza in new york"
    print(f"\n--- Testing Simple Search: '{query2}' ---")
    results2 = se.simple_search(query2, max_results=3)
    if results2:
        print(f"Success! Found {len(results2)} results.")
    else:
        print("FAILURE: No results found for query 2.")

if __name__ == "__main__":
    main()
