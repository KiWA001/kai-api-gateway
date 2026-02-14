"""
Free Proxy Manager for Browser Portals
--------------------------------------
Fetches and manages free proxy servers for ChatGPT and Copilot.
Automatically tests proxies to ensure they're active.
"""

import asyncio
import aiohttp
import random
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger("kai_api.proxy_manager")

@dataclass
class Proxy:
    """Represents a proxy server."""
    ip: str
    port: int
    country: str
    protocol: str = "http"
    last_tested: Optional[datetime] = None
    is_working: bool = False
    response_time: float = 0.0
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    def to_playwright_format(self) -> Dict:
        """Convert to Playwright proxy format."""
        return {
            "server": f"{self.protocol}://{self.ip}:{self.port}",
        }


class FreeProxyManager:
    """Manages free proxy servers for browser portals."""
    
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.current_proxy: Optional[Proxy] = None
        self.proxy_history: List[Proxy] = []
        self.max_history = 10
        
    async def fetch_proxies(self, limit: int = 20) -> List[Proxy]:
        """Fetch free proxies from multiple sources."""
        proxies = []
        
        # Source 1: proxylist.geonode.com
        try:
            url = f"https://proxylist.geonode.com/api/proxy-list?limit={limit}&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get('data', []):
                            proxy = Proxy(
                                ip=item['ip'],
                                port=int(item['port']),
                                country=item.get('country', 'Unknown'),
                                protocol=item.get('protocols', ['http'])[0] if isinstance(item.get('protocols'), list) else 'http'
                            )
                            proxies.append(proxy)
                            logger.info(f"Fetched proxy: {proxy}")
        except Exception as e:
            logger.warning(f"Failed to fetch from geonode: {e}")
        
        # Source 2: proxy-list.download
        try:
            url = "https://www.proxy-list.download/api/v1/get?type=http"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        lines = text.strip().split('\n')
                        for line in lines[:limit]:
                            if ':' in line:
                                ip, port = line.strip().split(':')
                                proxy = Proxy(
                                    ip=ip,
                                    port=int(port),
                                    country='Unknown',
                                    protocol='http'
                                )
                                if proxy not in proxies:
                                    proxies.append(proxy)
        except Exception as e:
            logger.warning(f"Failed to fetch from proxy-list: {e}")
        
        # Source 3: free-proxy-list.net (simple API)
        try:
            # This is a fallback - scrape a few common free proxies
            fallback_proxies = [
                ("20.235.104.105", 3128, "US"),
                ("159.89.49.172", 3128, "US"),
                ("20.210.113.32", 8123, "US"),
                ("103.152.232.142", 8080, "ID"),
                ("43.135.166.179", 8080, "SG"),
                ("47.74.152.190", 8888, "JP"),
                ("52.196.1.179", 8080, "JP"),
                ("13.231.21.152", 3128, "JP"),
                ("54.179.34.32", 3128, "SG"),
                ("18.141.176.104", 3128, "SG"),
            ]
            
            for ip, port, country in fallback_proxies:
                proxy = Proxy(ip=ip, port=port, country=country, protocol='http')
                if proxy not in proxies:
                    proxies.append(proxy)
                    
        except Exception as e:
            logger.warning(f"Fallback proxy error: {e}")
        
        logger.info(f"Total proxies fetched: {len(proxies)}")
        return proxies
    
    async def test_proxy(self, proxy: Proxy, test_url: str = "https://httpbin.org/ip") -> bool:
        """Test if a proxy is working."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start_time = asyncio.get_event_loop().time()
                
                async with session.get(
                    test_url, 
                    proxy=f"http://{proxy.ip}:{proxy.port}",
                    ssl=False
                ) as response:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    if response.status == 200:
                        proxy.is_working = True
                        proxy.response_time = elapsed
                        proxy.last_tested = datetime.now()
                        logger.info(f"✅ Proxy working: {proxy} ({elapsed:.2f}s)")
                        return True
                    else:
                        proxy.is_working = False
                        logger.warning(f"❌ Proxy failed with status {response.status}: {proxy}")
                        return False
                        
        except Exception as e:
            proxy.is_working = False
            logger.warning(f"❌ Proxy test failed: {proxy} - {str(e)}")
            return False
    
    async def get_working_proxy(self, max_attempts: int = 5) -> Optional[Proxy]:
        """Get a working proxy, testing multiple if needed."""
        # First, try to use current proxy if it exists and is working
        if self.current_proxy and self.current_proxy.is_working:
            # Retest it to make sure it's still working
            if await self.test_proxy(self.current_proxy):
                return self.current_proxy
        
        # Fetch new proxies if we don't have enough
        if len(self.proxies) < 5:
            logger.info("Fetching new proxies...")
            self.proxies = await self.fetch_proxies(limit=30)
        
        # Test proxies until we find a working one
        random.shuffle(self.proxies)  # Randomize to distribute load
        
        for i, proxy in enumerate(self.proxies[:max_attempts]):
            logger.info(f"Testing proxy {i+1}/{max_attempts}: {proxy}")
            
            if await self.test_proxy(proxy):
                # Save current to history
                if self.current_proxy:
                    self.proxy_history.insert(0, self.current_proxy)
                    if len(self.proxy_history) > self.max_history:
                        self.proxy_history.pop()
                
                self.current_proxy = proxy
                return proxy
        
        logger.error("No working proxy found!")
        return None
    
    async def rotate_proxy(self) -> Optional[Proxy]:
        """Rotate to a new working proxy."""
        logger.info("Rotating to new proxy...")
        
        # Mark current as not working
        if self.current_proxy:
            self.current_proxy.is_working = False
        
        # Get a new working proxy
        return await self.get_working_proxy()
    
    def get_current_proxy(self) -> Optional[Proxy]:
        """Get the current active proxy."""
        return self.current_proxy
    
    def get_proxy_stats(self) -> Dict:
        """Get statistics about proxies."""
        working = sum(1 for p in self.proxies if p.is_working)
        return {
            "total_proxies": len(self.proxies),
            "working_proxies": working,
            "current_proxy": str(self.current_proxy) if self.current_proxy else None,
            "proxy_history": [str(p) for p in self.proxy_history[:5]]
        }


# Global proxy manager instance
_proxy_manager: Optional[FreeProxyManager] = None

def get_proxy_manager() -> FreeProxyManager:
    """Get the global proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = FreeProxyManager()
    return _proxy_manager
