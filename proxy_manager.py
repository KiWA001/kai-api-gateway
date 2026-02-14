"""
Free Proxy Manager for Browser Portals
--------------------------------------
Fetches and manages free proxy servers for ChatGPT and Copilot.
Automatically tests proxies and keeps ONLY working ones.
"""

import asyncio
import aiohttp
import random
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime

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
    response_time: float = 999.0
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    def to_playwright_format(self) -> Dict:
        """Convert to Playwright proxy format."""
        return {
            "server": f"{self.protocol}://{self.ip}:{self.port}",
        }
    
    def __hash__(self):
        return hash((self.ip, self.port))
    
    def __eq__(self, other):
        if isinstance(other, Proxy):
            return self.ip == other.ip and self.port == other.port
        return False


class FreeProxyManager:
    """Manages free proxy servers - keeps ONLY working ones."""
    
    def __init__(self):
        self.working_proxies: List[Proxy] = []  # ONLY working proxies stored here
        self.current_proxy_index: int = 0
        self.current_proxy: Optional[Proxy] = None
        
    async def fetch_and_filter_proxies(self, max_test: int = 20) -> List[Proxy]:
        """
        Fetch proxies and test them, keeping ONLY working ones.
        Returns list of verified working proxies.
        """
        logger.info("🔍 Fetching fresh proxies...")
        
        # Fetch from multiple sources
        all_proxies = await self._fetch_from_sources()
        
        if not all_proxies:
            logger.error("❌ No proxies fetched from any source")
            return []
        
        logger.info(f"📊 Fetched {len(all_proxies)} total proxies, testing up to {max_test}...")
        
        # Shuffle for variety
        random.shuffle(all_proxies)
        
        # Test proxies and collect working ones
        working = []
        tested = 0
        
        for proxy in all_proxies:
            if tested >= max_test:
                break
                
            tested += 1
            logger.info(f"🧪 Testing proxy {tested}/{max_test}: {proxy.ip}:{proxy.port}")
            
            if await self._test_proxy_quick(proxy):
                working.append(proxy)
                logger.info(f"✅ WORKING! ({proxy.response_time:.2f}s) - Total working: {len(working)}")
                
                # Stop once we have enough working proxies
                if len(working) >= 5:
                    logger.info("✨ Found 5 working proxies, stopping tests")
                    break
            else:
                logger.debug(f"❌ Dead proxy: {proxy.ip}:{proxy.port}")
        
        # REPLACE the list with ONLY working proxies
        self.working_proxies = working
        self.current_proxy_index = 0
        
        if working:
            self.current_proxy = working[0]
            logger.info(f"🎯 Kept {len(working)} WORKING proxies out of {tested} tested")
        else:
            self.current_proxy = None
            logger.warning("⚠️ No working proxies found!")
        
        return working
    
    async def _fetch_from_sources(self) -> List[Proxy]:
        """Fetch proxies from multiple free sources."""
        proxies = []
        
        # Source 1: Free proxy list (HTTP)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(
                    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        lines = text.strip().split('\n')
                        for line in lines[:100]:  # Limit to first 100
                            if ':' in line:
                                parts = line.strip().split(':')
                                if len(parts) >= 2:
                                    try:
                                        proxy = Proxy(
                                            ip=parts[0],
                                            port=int(parts[1]),
                                            country='Unknown',
                                            protocol='http'
                                        )
                                        proxies.append(proxy)
                                    except:
                                        pass
                        logger.info(f"✅ Source 1: Got {len(proxies)} proxies")
        except Exception as e:
            logger.warning(f"❌ Source 1 failed: {e}")
        
        # Source 2: Alternative proxy list
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(
                    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        lines = text.strip().split('\n')
                        new_count = 0
                        for line in lines[:100]:
                            if ':' in line:
                                parts = line.strip().split(':')
                                if len(parts) >= 2:
                                    try:
                                        proxy = Proxy(
                                            ip=parts[0],
                                            port=int(parts[1]),
                                            country='Unknown',
                                            protocol='http'
                                        )
                                        if proxy not in proxies:
                                            proxies.append(proxy)
                                            new_count += 1
                                    except:
                                        pass
                        logger.info(f"✅ Source 2: Got {new_count} new proxies")
        except Exception as e:
            logger.warning(f"❌ Source 2 failed: {e}")
        
        # Source 3:geonode free proxies API
        try:
            url = "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols=http"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        new_count = 0
                        for item in data.get('data', []):
                            try:
                                proxy = Proxy(
                                    ip=item['ip'],
                                    port=int(item['port']),
                                    country=item.get('country', 'Unknown'),
                                    protocol='http'
                                )
                                if proxy not in proxies:
                                    proxies.append(proxy)
                                    new_count += 1
                            except:
                                pass
                        logger.info(f"✅ Source 3: Got {new_count} new proxies")
        except Exception as e:
            logger.warning(f"❌ Source 3 failed: {e}")
        
        # Remove duplicates
        unique_proxies = list({(p.ip, p.port): p for p in proxies}.values())
        logger.info(f"📦 Total unique proxies: {len(unique_proxies)}")
        
        return unique_proxies
    
    async def _test_proxy_quick(self, proxy: Proxy) -> bool:
        """Quick test if proxy is working (5 second timeout)."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)  # Quick 5 second test
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start = asyncio.get_event_loop().time()
                
                # Test with a simple, fast endpoint
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=f"http://{proxy.ip}:{proxy.port}",
                    ssl=False
                ) as response:
                    elapsed = asyncio.get_event_loop().time() - start
                    
                    if response.status == 200:
                        proxy.is_working = True
                        proxy.response_time = elapsed
                        proxy.last_tested = datetime.now()
                        return True
                    return False
                        
        except Exception as e:
            proxy.is_working = False
            return False
    
    def get_next_working_proxy(self) -> Optional[Proxy]:
        """Get next working proxy from rotation."""
        if not self.working_proxies:
            logger.warning("No working proxies available!")
            return None
        
        # Move to next proxy
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
        self.current_proxy = self.working_proxies[self.current_proxy_index]
        
        logger.info(f"🔄 Rotated to proxy {self.current_proxy_index + 1}/{len(self.working_proxies)}: {self.current_proxy}")
        return self.current_proxy
    
    def get_current_proxy(self) -> Optional[Proxy]:
        """Get currently selected proxy."""
        return self.current_proxy
    
    def get_working_proxy_list(self) -> List[Proxy]:
        """Get list of all working proxies."""
        return self.working_proxies.copy()
    
    def get_stats(self) -> Dict:
        """Get proxy statistics."""
        return {
            "working_proxies": len(self.working_proxies),
            "current_proxy_index": self.current_proxy_index + 1 if self.working_proxies else 0,
            "current_proxy": str(self.current_proxy) if self.current_proxy else None,
        }


# Global proxy manager instance
_proxy_manager: Optional[FreeProxyManager] = None

def get_proxy_manager() -> FreeProxyManager:
    """Get the global proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = FreeProxyManager()
    return _proxy_manager
