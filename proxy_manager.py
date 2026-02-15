"""
Proxy Manager for Browser Portals
---------------------------------
Supports custom IP proxy configuration with optional authentication.
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger("kai_api.proxy_manager")

@dataclass
class Proxy:
    """Represents a proxy server with optional authentication."""
    ip: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    country: str = "Custom"
    last_tested: Optional[datetime] = None
    is_working: bool = False
    response_time: float = 999.0
    
    def __str__(self):
        """Return proxy URL string."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    def to_display_string(self) -> str:
        """Return proxy URL without credentials for display."""
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    def to_playwright_format(self) -> Dict:
        """Convert to Playwright proxy format."""
        proxy_dict = {
            "server": f"{self.protocol}://{self.ip}:{self.port}",
        }
        
        # Add authentication if present
        if self.username:
            proxy_dict["username"] = self.username
        if self.password:
            proxy_dict["password"] = self.password
            
        return proxy_dict


class ProxyManager:
    """Manages proxy configuration with optional authentication."""
    
    def __init__(self):
        self.custom_proxy: Optional[Proxy] = None
        self._proxy_str: Optional[str] = None
        
    def set_custom_proxy(self, proxy_str: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Set a custom proxy from string format.
        Supports formats:
        - ip:port
        - protocol://ip:port
        - protocol://username:password@ip:port
        - ip:port (with separate username/password params)
        
        Examples: 
        - 192.168.1.1:8080
        - http://proxy.example.com:3128
        - http://user:pass@proxy.example.com:3128
        """
        try:
            proxy_str = proxy_str.strip()
            
            # Check if credentials are embedded in URL
            parsed = urlparse(proxy_str)
            
            # Parse protocol
            protocol = parsed.scheme or "http"
            
            # Get host and port
            host = parsed.hostname
            port = parsed.port
            
            # If no host parsed, try simple ip:port format
            if not host:
                if ":" not in proxy_str:
                    raise ValueError("Proxy must include port (e.g., ip:port)")
                
                # Remove protocol if present
                if "://" in proxy_str:
                    protocol, proxy_str = proxy_str.split("://", 1)
                
                parts = proxy_str.rsplit(":", 1)
                host = parts[0]
                port = int(parts[1])
            
            # Extract credentials from URL if present
            url_username = parsed.username
            url_password = parsed.password
            
            # Use provided credentials or extracted ones
            final_username = username or url_username
            final_password = password or url_password
            
            self.custom_proxy = Proxy(
                ip=host,
                port=port,
                protocol=protocol,
                username=final_username,
                password=final_password,
                is_working=True,  # Assume working until tested
                last_tested=datetime.now()
            )
            self._proxy_str = str(self.custom_proxy)
            
            auth_info = f" with auth" if final_username else ""
            logger.info(f"✅ Custom proxy set: {self.custom_proxy.to_display_string()}{auth_info}")
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
            
            # Build proxy URL with auth if present
            if test_proxy.username and test_proxy.password:
                proxy_url = f"{test_proxy.protocol}://{test_proxy.username}:{test_proxy.password}@{test_proxy.ip}:{test_proxy.port}"
            else:
                proxy_url = f"{test_proxy.protocol}://{test_proxy.ip}:{test_proxy.port}"
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start = asyncio.get_event_loop().time()
                
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url,
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
            "proxy": self.custom_proxy.to_display_string(),
            "full_url": str(self.custom_proxy),
            "protocol": self.custom_proxy.protocol,
            "ip": self.custom_proxy.ip,
            "port": self.custom_proxy.port,
            "has_auth": bool(self.custom_proxy.username),
            "username": self.custom_proxy.username,
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
