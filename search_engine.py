"""
Search Engine
-------------
Handles web search and content extraction for Deep Research.
Uses 'duckduckgo-search' for privacy-friendly, reverse-engineered search.
Uses 'requests' + 'beautifulsoup4' for scraping.
"""

import logging
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("kai_api.search")

class SearchEngine:
    def __init__(self):
        self.ddgs = DDGS()
        # Use a more realistic browser header set
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }

    def simple_search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Perform a simple text search using DuckDuckGo.
        Tries multiple backends (api, html, lite) for robustness.
        Returns: [{'title': str, 'href': str, 'body': str}, ...]
        """
        backends = ["api", "html", "lite"]
        for backend in backends:
            try:
                logger.info(f"Searching '{query}' using backend='{backend}'...")
                results = list(self.ddgs.text(query, max_results=max_results, backend=backend))
                if results:
                    logger.info(f"Found {len(results)} results via '{backend}'")
                    return results
            except Exception as e:
                logger.warning(f"Search backend '{backend}' failed: {e}")
        
        logger.error(f"All 'ddgs' library backends failed. Attempting manual scraper fallback...")
        return self._manual_search_ddg_html(query, max_results)

    def _manual_search_ddg_html(self, query: str, max_results: int) -> list[dict]:
        """
        Fallback: Manually scrape html.duckduckgo.com if the library fails.
        """
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}
            # Use existing headers
            resp = requests.post(url, data=data, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            results = []
            
            # DDG HTML Structure: .web-result
            for result in soup.select(".web-result"):
                if len(results) >= max_results:
                    break
                    
                title_tag = result.select_one(".result__a")
                if not title_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href')
                snippet_tag = result.select_one(".result__snippet")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                if href and title:
                    results.append({
                        "title": title,
                        "href": href,
                        "body": snippet
                    })
            
            logger.info(f"Manual fallback found {len(results)} results.")
            return results
            
        except Exception as e:
            logger.error(f"Manual scraper failed: {e}")
            return []

    def fetch_page_content(self, url: str) -> str:
        """
        Fetch and parse a webpage. Returns properly formatted text.
        """
        try:
            # 5-second timeout is aggressive but necessary for responsiveness
            resp = requests.get(url, headers=self.headers, timeout=5)
            resp.raise_for_status()
            
            # Use lxml for speed if available, else html.parser
            soup = BeautifulSoup(resp.content, 'lxml')
            
            # Kill distracting elements
            for tag in soup(["script", "style", "nav", "footer", "header", "form", "iframe", "svg"]):
                tag.decompose()
                
            # Extract text
            text = soup.get_text(separator=' ')
            
            # collapse whitespace
            tokens = text.split()
            clean_text = ' '.join(tokens)
            
            # Return modest amount
            return clean_text[:5000]
            
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e} (Status: {getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') else 'N/A'})")
            return ""

    def deep_research_gather(self, query: str, breadth: int = 5) -> str:
        """
        Search for a query, then fetch the content of the top N results.
        Returns a massive context string.
        """
        logger.info(f"Deep Research Gathering for: {query}")
        
        # 1. Search
        results = self.simple_search(query, max_results=breadth)
        if not results:
            return ""

        # 2. Parallel Fetch
        context = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_result = {executor.submit(self.fetch_page_content, r['href']): r for r in results}
            
            for future in future_to_result:
                r = future_to_result[future]
                try:
                    content = future.result()
                    if content and len(content) > 100:
                        context.append(f"=== SOURCE: {r['title']} ({r['href']}) ===\n{content}\n")
                    else:
                        # Fallback to snippet
                        context.append(f"=== SOURCE (Snippet Only): {r['title']} ({r['href']}) ===\n{r.get('body', '')}\n")
                except Exception:
                     # Fallback to snippet on crash
                    context.append(f"=== SOURCE (Snippet Only): {r['title']} ({r['href']}) ===\n{r.get('body', '')}\n")
                    
        return "\n".join(context)
