"""
Authentication Module
---------------------
Shared authentication logic for dashboard vs external API access.
"""

from fastapi import HTTPException, Request, Header
from typing import Optional
from db import get_supabase
from config import DEMO_API_KEY

# List of allowed origins/paths that don't need API key (dashboard access)
DASHBOARD_PATHS = ["/", "/docs/public", "/docs", "/static/"]
DASHBOARD_HOSTS = ["localhost", "127.0.0.1"]  # Add your domain here when deployed

async def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """
    Verify Bearer Token or X-API-KEY.
    Dashboard requests (from same origin) don't need API key.
    External API calls (from other origins) require API key.
    Web searches require key but don't deduct tokens.
    
    Returns: key_data (dict) 
    Raises: HTTPException if invalid
    """
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    
    if not token and x_api_key:
        token = x_api_key
    
    # Check if request is coming from dashboard (same origin)
    referer = request.headers.get("referer", "")
    origin = request.headers.get("origin", "")
    
    # Check if referer/origin matches dashboard
    is_dashboard_request = False
    
    # Check if referer contains dashboard paths
    for path in DASHBOARD_PATHS:
        if path in referer:
            is_dashboard_request = True
            break
    
    # Also check if origin is localhost (local development)
    for host in DASHBOARD_HOSTS:
        if host in origin or host in referer:
            is_dashboard_request = True
            break
    
    # Check if it's a browser request (has Accept: text/html)
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and (referer or origin):
        is_dashboard_request = True
    
    if not token:
        if is_dashboard_request:
            # Dashboard access - no key needed
            return {"id": "dashboard", "name": "Dashboard User", "limit_tokens": -1, "is_dashboard": True}
        else:
            # External API call - key required
            raise HTTPException(
                status_code=401, 
                detail="Authorization header required. Use 'Authorization: Bearer YOUR_API_KEY'. Get a key from the dashboard."
            )

    # 1. Check Demo Key
    if token == DEMO_API_KEY:
        return {"id": "demo", "name": "Demo User", "limit_tokens": -1, "is_dashboard": False}

    # 2. Check Database (Non-blocking)
    import asyncio
    loop = asyncio.get_event_loop()
    
    def _sync_check():
        supabase = get_supabase()
        if not supabase:
             raise HTTPException(status_code=503, detail="Service unavailable")
             
        res = supabase.table("api_keys").select("*").eq("token", token).execute()
        if not res.data:
            return None
        return res.data[0]

    try:
        key_data = await loop.run_in_executor(None, _sync_check)
        
        if not key_data:
             raise HTTPException(status_code=401, detail="Incorrect API key provided")
        
        if not key_data.get("is_active", True):
            raise HTTPException(status_code=403, detail="API Key is inactive")
            
        # Check limits
        current_usage = key_data.get("usage_tokens", 0)
        limit = key_data.get("limit_tokens", 0)
        
        if limit > 0 and current_usage >= limit:
             raise HTTPException(status_code=429, detail="You have exceeded your current quota")
             
        key_data["is_dashboard"] = False
        return key_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
