import logging
from googlesearch import search

logging.basicConfig(level=logging.INFO)

def main():
    query = "python async await tutorial"
    print(f"Searching Google for: '{query}'")
    
    try:
        # advanced=True returns SearchResult objects with title/desc/url
        results = search(query, num_results=3, advanced=True)
        count = 0
        for r in results:
            count += 1
            print(f"[{count}] {r.title}")
            print(f"    {r.url}")
            print(f"    {r.description}")
            if count >= 3:
                break
        
        if count == 0:
            print("No results found.")
            
    except Exception as e:
        print(f"Google Search Error: {e}")

if __name__ == "__main__":
    main()
