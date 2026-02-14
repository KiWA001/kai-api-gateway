"""
Proxy Manager for Browser Portals
---------------------------------
Supports custom IP proxy configuration for the entire container.
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("kai_api.proxy_manager")

@dataclass
class Proxy:
    """Represents a proxy server."""
    ip: str
    port: int
    country: str = "Custom"
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


class ProxyManager:
    """Manages proxy configuration - primarily for custom IP."""
    
    def __init__(self):
        self.custom_proxy: Optional[Proxy] = None
        self._proxy_str: Optional[str] = None
        
    def set_custom_proxy(self, proxy_str: str) -> bool:
        """
        Set a custom proxy from string format: ip:port or protocol://ip:port
        Examples: 192.168.1.1:8080, http://proxy.example.com:3128
        """
        try:
            proxy_str = proxy_str.strip()
            
            # Parse protocol if provided
            protocol = "http"
            if "://" in proxy_str:
                protocol, proxy_str = proxy_str.split("://", 1)
            
            # Parse IP and port
            if ":" not in proxy_str:
                raise ValueError("Proxy must include port (e.g., ip:port)")
            
            parts = proxy_str.rsplit(":", 1)
            ip = parts[0]
            port = int(parts[1])
            
            self.custom_proxy = Proxy(
                ip=ip,
                port=port,
                protocol=protocol,
                is_working=True,  # Assume working until tested
                last_tested=datetime.now()
            )
            self._proxy_str = f"{protocol}://{ip}:{port}"
            
            logger.info(f"✅ Custom proxy set: {self._proxy_str}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set custom proxy: {e}")
            return False
    
    def clear_proxy(self):
        """Clear the custom proxy."""
        self.custom_proxy = None
        self._proxy_str = None
        logger.info("🗑️ Custom proxy cleared")
    
    def get_current_proxy(self) -> Optional[Proxy]:
        """Get the current custom proxy."""
        return self.custom_proxy
    
    def get_proxy_string(self) -> Optional[str]:
        """Get the proxy string for environment variables."""
        return self._proxy_str
    
    async def test_proxy(self, proxy: Optional[Proxy] = None) -> bool:
        """Test if a proxy is working."""
        test_proxy = proxy or self.custom_proxy
        if not test_proxy:
            return False
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start = asyncio.get_event_loop().time()
                
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=f"{test_proxy.protocol}://{test_proxy.ip}:{test_proxy.port}",
                    ssl=False
                ) as response:
                    elapsed = asyncio.get_event_loop().time() - start
                    
                    if response.status == 200:
                        test_proxy.is_working = True
                        test_proxy.response_time = elapsed
                        test_proxy.last_tested = datetime.now()
                        logger.info(f"✅ Proxy test passed: {elapsed:.2f}s")
                        return True
                    return False
                        
        except Exception as e:
            logger.warning(f"❌ Proxy test failed: {e}")
            test_proxy.is_working = False
            return False
    
    def get_status(self) -> Dict:
        """Get proxy status."""
        if not self.custom_proxy:
            return {
                "enabled": False,
                "proxy": None,
                "message": "No custom proxy configured"
            }
        
        return {
            "enabled": True,
            "proxy": str(self.custom_proxy),
            "protocol": self.custom_proxy.protocol,
            "ip": self.custom_proxy.ip,
            "port": self.custom_proxy.port,
            "is_working": self.custom_proxy.is_working,
            "response_time": f"{self.custom_proxy.response_time:.2f}s",
            "last_tested": self.custom_proxy.last_tested.isoformat() if self.custom_proxy.last_tested else None
        }


# Global proxy manager instance
_proxy_manager: Optional[ProxyManager] = None

def get_proxy_manager() -> ProxyManager:
    """Get the global proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager
