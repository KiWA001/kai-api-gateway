from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import secrets
import uuid
import asyncio

from db import get_supabase

router = APIRouter(prefix="/qaz", tags=["Admin"])

# --- Models ---

class APIKey(BaseModel):
    id: str
    name: str
    token: str
    usage_tokens: int
    limit_tokens: int
    created_at: str
    is_active: bool

class CreateKeyRequest(BaseModel):
    name: str
    limit_tokens: Optional[int] = 1000000

class LookupKeyRequest(BaseModel):
    token: str

# --- Endpoints ---

@router.get("/keys", response_model=List[APIKey])
async def list_keys():
    """List all API keys."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        res = supabase.table("api_keys").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys", response_model=APIKey)
async def create_key(req: CreateKeyRequest):
    """Create a new API key."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    # Generate a secure token
    token = f"sk-kai-{secrets.token_urlsafe(16)}"
    
    new_key = {
        "name": req.name,
        "token": token,
        "limit_tokens": req.limit_tokens,
        "usage_tokens": 0,
        "is_active": True
    }
    
    try:
        res = supabase.table("api_keys").insert(new_key).execute()
        if res.data:
            return res.data[0]
        raise HTTPException(status_code=500, detail="Failed to create key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/keys/{key_id}")
async def revoke_key(key_id: str):
    """Revoke (delete) an API key."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        # Check if exists first? Or just delete.
        # Hard delete for now, or soft delete if we had is_active column logic in router update, but delete is cleaner for management
        res = supabase.table("api_keys").delete().eq("id", key_id).execute()
        return {"status": "success", "deleted": key_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys/{key_id}/reset")
async def reset_usage(key_id: str):
    """Reset usage for a key."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        supabase.table("api_keys").update({"usage_tokens": 0}).eq("id", key_id).execute()
        return {"status": "reset"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.post("/keys/lookup")
async def lookup_key_by_token(req: LookupKeyRequest):
    """Lookup API key usage by token (for public dashboard)."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    if not req.token or not req.token.startswith("sk-"):
        raise HTTPException(status_code=400, detail="Invalid token format")
    
    try:
        res = supabase.table("api_keys").select("*").eq("token", req.token).execute()
        
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail="Key not found")
        
        key = res.data[0]
        
        # Return limited info (don't expose full token)
        return {
            "name": key.get("name"),
            "usage_tokens": key.get("usage_tokens", 0),
            "limit_tokens": key.get("limit_tokens", 0),
            "remaining": key.get("limit_tokens", 0) - key.get("usage_tokens", 0),
            "created_at": key.get("created_at"),
            "is_active": key.get("is_active", True)
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'message'):
            error_msg = str(e.message)
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_msg = str(e.args[0])
        raise HTTPException(status_code=500, detail=error_msg)

# --- Copilot CAPTCHA Handling ---

@router.get("/copilot/captcha/status")
async def copilot_captcha_status():
    """Check if Copilot has a pending CAPTCHA challenge."""
    try:
        from providers.copilot_provider import CopilotProvider
        
        is_pending = CopilotProvider.is_captcha_pending()
        
        if is_pending:
            # Check if screenshot exists
            import os
            screenshot_path = "/tmp/copilot_captcha.png"
            has_screenshot = os.path.exists(screenshot_path)
            
            return {
                "captcha_required": True,
                "has_screenshot": has_screenshot,
                "screenshot_url": "/qaz/copilot/captcha/screenshot" if has_screenshot else None,
                "message": "CAPTCHA verification required. Please solve it in the admin panel."
            }
        else:
            return {
                "captcha_required": False,
                "message": "No CAPTCHA pending"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/copilot/captcha/screenshot")
async def copilot_captcha_screenshot():
    """Get the CAPTCHA screenshot for solving."""
    import os
    from fastapi.responses import FileResponse
    
    screenshot_path = "/tmp/copilot_captcha.png"
    
    if not os.path.exists(screenshot_path):
        raise HTTPException(status_code=404, detail="No CAPTCHA screenshot available")
    
    return FileResponse(screenshot_path, media_type="image/png")

@router.post("/copilot/captcha/solved")
async def copilot_captcha_solved():
    """Mark CAPTCHA as solved and save session."""
    try:
        from providers.copilot_provider import CopilotProvider
        from copilot_session import CopilotSessionManager
        
        # Get the context with CAPTCHA
        context = CopilotProvider.get_captcha_context()
        
        if not context:
            raise HTTPException(status_code=400, detail="No CAPTCHA context found")
        
        # Wait a bit for user to solve
        await asyncio.sleep(2)
        
        # Save cookies from the solved session
        cookies = await context.cookies()
        session_mgr = CopilotSessionManager()
        session_mgr.save_cookies(cookies)
        
        # Clear the pending state
        CopilotProvider.clear_captcha_pending()
        
        # Close the context
        await context.close()
        
        return {
            "status": "success",
            "message": "CAPTCHA solved and session saved"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/copilot/captcha/clear")
async def copilot_captcha_clear():
    """Clear the CAPTCHA pending state (for retry)."""
    try:
        from providers.copilot_provider import CopilotProvider
        
        # Get context and close it
        context = CopilotProvider.get_captcha_context()
        if context:
            await context.close()
        
        CopilotProvider.clear_captcha_pending()
        
        return {
            "status": "success",
            "message": "CAPTCHA state cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/copilot/session/status")
async def copilot_session_status():
    """Check Copilot session status."""
    try:
        from copilot_session import CopilotSessionManager
        
        session_info = CopilotSessionManager.get_session_info()
        return session_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Interactive Copilot Portal ---

@router.post("/copilot/portal/start")
async def start_copilot_portal():
    """Start the interactive Copilot browser portal."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        await portal.initialize()
        
        return {
            "status": "success",
            "message": "Portal started successfully",
            "initialized": portal.is_initialized
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/copilot/portal/screenshot")
async def get_portal_screenshot():
    """Get the latest portal screenshot."""
    import os
    from fastapi.responses import FileResponse
    
    try:
        from copilot_portal import get_portal
        portal = get_portal()
        
        if not portal.is_initialized:
            raise HTTPException(status_code=400, detail="Portal not initialized. Start it first.")
        
        # Take fresh screenshot
        await portal.take_screenshot()
        
        screenshot_path = "/tmp/copilot_portal.png"
        if not os.path.exists(screenshot_path):
            raise HTTPException(status_code=404, detail="Screenshot not available")
        
        return FileResponse(screenshot_path, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PortalMessage(BaseModel):
    message: str

@router.post("/copilot/portal/send")
async def send_portal_message(req: PortalMessage):
    """Send a message through the portal."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        
        if not portal.is_initialized:
            raise HTTPException(status_code=400, detail="Portal not initialized. Start it first.")
        
        response = await portal.send_message(req.message)
        
        return {
            "status": "success",
            "response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/copilot/portal/newchat")
async def portal_new_chat():
    """Click New Chat button in the portal."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        
        if not portal.is_initialized:
            raise HTTPException(status_code=400, detail="Portal not initialized. Start it first.")
        
        await portal.click_new_chat()
        
        return {
            "status": "success",
            "message": "New chat clicked"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/copilot/portal/refresh")
async def portal_refresh():
    """Refresh the portal page."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        
        if not portal.is_initialized:
            raise HTTPException(status_code=400, detail="Portal not initialized. Start it first.")
        
        await portal.refresh_page()
        
        return {
            "status": "success",
            "message": "Page refreshed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/copilot/portal/close")
async def close_copilot_portal():
    """Close the portal browser."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        await portal.close()
        
        return {
            "status": "success",
            "message": "Portal closed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PortalClick(BaseModel):
    x: float
    y: float

@router.post("/copilot/portal/click")
async def portal_click(req: PortalClick):
    """Click at specific coordinates on the portal page."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        
        if not portal.is_initialized:
            raise HTTPException(status_code=400, detail="Portal not initialized. Start it first.")
        
        await portal.click_at_coordinates(req.x, req.y)
        
        return {
            "status": "success",
            "message": f"Clicked at coordinates ({req.x}, {req.y})"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copilot/portal/click_checkbox")
async def portal_click_checkbox():
    """Click on the CAPTCHA checkbox (estimated position)."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        
        if not portal.is_initialized:
            raise HTTPException(status_code=400, detail="Portal not initialized. Start it first.")
        
        # CAPTCHA checkbox is typically in the center of the screen
        # Based on 1280x800 viewport, center is approximately (640, 400)
        # The checkbox in your screenshot appears to be slightly above center
        await portal.click_at_coordinates(640, 350)
        
        return {
            "status": "success",
            "message": "Clicked CAPTCHA checkbox area"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
