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

class PortalMessage(BaseModel):
    message: str

class PortalProviderRequest(BaseModel):
    provider: str  # "copilot", "huggingchat", "chatgpt", "gemini", "zai"

# --- Endpoints ---

@router.get("/keys", response_model=List[APIKey])
async def list_keys():
    """List all API keys."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    try:
        res = supabase.table("kaiapi_api_keys").select("*").order("created_at", desc=True).execute()
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
        res = supabase.table("kaiapi_api_keys").insert(new_key).execute()
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
        res = supabase.table("kaiapi_api_keys").delete().eq("id", key_id).execute()
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
        supabase.table("kaiapi_api_keys").update({"usage_tokens": 0}).eq("id", key_id).execute()
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
        res = supabase.table("kaiapi_api_keys").select("*").eq("token", req.token).execute()
        
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


@router.get("/copilot/portal/status")
async def get_portal_status():
    """Check if the portal is currently running."""
    try:
        from copilot_portal import get_portal
        
        portal = get_portal()
        is_running = portal.is_running()
        
        return {
            "is_running": is_running,
            "is_initialized": portal.is_initialized
        }
    except Exception as e:
        return {
            "is_running": False,
            "is_initialized": False,
            "error": str(e)
        }


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


# --- NEW: Unified Browser Portal System for ALL Providers ---

class UnifiedPortalAction(BaseModel):
    provider: str  # "copilot", "huggingchat", "chatgpt", "gemini", "zai"
    action: str    # "click", "type", "keypress", "scroll", "focus"
    x: Optional[float] = None
    y: Optional[float] = None
    text: Optional[str] = None
    key: Optional[str] = None
    delta_x: Optional[int] = 0
    delta_y: Optional[int] = 0

@router.post("/portal/start")
async def start_unified_portal(req: PortalProviderRequest):
    """Start an interactive browser portal for any provider."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        provider = PortalProvider(req.provider.lower())
        portal = get_portal_manager().get_portal(provider)
        
        if portal.is_running():
            return {
                "status": "already_running",
                "provider": req.provider,
                "message": f"{provider.value} portal is already running"
            }
        
        await portal.initialize(headless=True)
        
        return {
            "status": "success",
            "provider": req.provider,
            "message": f"{provider.value} portal started successfully",
            "requires_login": portal.config.requires_login,
            "url": portal.config.url
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portal/{provider}/screenshot")
async def get_unified_portal_screenshot(provider: str, quality: float = 1.0, format: str = "png"):
    """Get screenshot from any provider portal with optional quality/compression."""
    import os
    from fastapi.responses import FileResponse, StreamingResponse
    from PIL import Image
    import io
    
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running. Start it first.")
        
        await portal.take_screenshot()
        
        if not os.path.exists(portal.screenshot_path):
            raise HTTPException(status_code=404, detail="Screenshot not available")
        
        # If quality is 1.0 and format is png, return as-is
        if quality >= 1.0 and format == "png":
            return FileResponse(portal.screenshot_path, media_type="image/png")
        
        # Otherwise, compress/process the image
        img = Image.open(portal.screenshot_path)
        
        # Resize if quality < 1.0
        if quality < 1.0:
            new_size = (int(img.width * quality), int(img.height * quality))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to desired format
        img_io = io.BytesIO()
        if format == "jpeg" or format == "jpg":
            img = img.convert("RGB")
            img.save(img_io, format="JPEG", quality=int(quality * 100) if quality < 1 else 85)
            media_type = "image/jpeg"
        else:
            img.save(img_io, format="PNG")
            media_type = "image/png"
        
        img_io.seek(0)
        return StreamingResponse(img_io, media_type=media_type)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# MJPEG Streaming endpoint for video-like experience
@router.get("/portal/{provider}/stream")
async def stream_portal_video(provider: str, quality: float = 0.5, fps: int = 2):
    """Stream the portal as MJPEG for video-like experience."""
    import os
    import asyncio
    from fastapi.responses import StreamingResponse
    from PIL import Image
    import io
    
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running")
        
        async def generate_frames():
            """Generate MJPEG stream."""
            frame_delay = 1.0 / fps
            
            while portal.is_running():
                try:
                    # Take screenshot
                    await portal.take_screenshot()
                    
                    if os.path.exists(portal.screenshot_path):
                        # Process image
                        img = Image.open(portal.screenshot_path)
                        
                        if quality < 1.0:
                            new_size = (int(img.width * quality), int(img.height * quality))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Convert to JPEG for smaller size
                        img = img.convert("RGB")
                        img_io = io.BytesIO()
                        img.save(img_io, format="JPEG", quality=70)
                        img_io.seek(0)
                        
                        frame_data = img_io.getvalue()
                        
                        # Yield MJPEG frame
                        yield (
                            b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n'
                            b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n'
                            b'\r\n' + frame_data + b'\r\n'
                        )
                    
                    await asyncio.sleep(frame_delay)
                    
                except Exception as e:
                    print(f"Stream error: {e}")
                    await asyncio.sleep(frame_delay)
        
        return StreamingResponse(
            generate_frames(),
            media_type="multipart/x-mixed-replace;boundary=frame"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal/action")
async def unified_portal_action(req: UnifiedPortalAction):
    """Perform an action on any provider portal."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        provider = PortalProvider(req.provider.lower())
        portal = get_portal_manager().get_portal(provider)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{req.provider} portal not running. Start it first.")
        
        result = {}
        
        if req.action == "click":
            if req.x is None or req.y is None:
                raise HTTPException(status_code=400, detail="x and y coordinates required for click")
            await portal.click(req.x, req.y)
            result = {"message": f"Clicked at ({req.x}, {req.y})"}
            
        elif req.action == "type":
            if not req.text:
                raise HTTPException(status_code=400, detail="text required for type action")
            await portal.type_text(req.text)
            result = {"message": f"Typed: {req.text[:50]}..." if len(req.text) > 50 else f"Typed: {req.text}"}
            
        elif req.action == "keypress":
            if not req.key:
                raise HTTPException(status_code=400, detail="key required for keypress action")
            await portal.key_press(req.key)
            result = {"message": f"Pressed key: {req.key}"}
            
        elif req.action == "scroll":
            await portal.scroll(req.delta_x or 0, req.delta_y or 0)
            result = {"message": f"Scrolled by ({req.delta_x}, {req.delta_y})"}
            
        elif req.action == "focus":
            if req.x is None or req.y is None:
                raise HTTPException(status_code=400, detail="x and y coordinates required for focus")
            await portal.focus_input(req.x, req.y)
            result = {"message": f"Focused input at ({req.x}, {req.y})"}
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
        
        return {
            "status": "success",
            "provider": req.provider,
            "action": req.action,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal/{provider}/send")
async def unified_portal_send_message(provider: str, req: PortalMessage):
    """Send a message through any provider portal."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running. Start it first.")
        
        response = await portal.send_message(req.message)
        
        return {
            "status": "success",
            "provider": provider,
            "response": response
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal/{provider}/newchat")
async def unified_portal_new_chat(provider: str):
    """Start new chat on any provider portal."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running. Start it first.")
        
        await portal.new_chat()
        
        return {
            "status": "success",
            "provider": provider,
            "message": "New chat started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal/{provider}/close")
async def close_unified_portal(provider: str):
    """Close any provider portal."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        await portal.close()
        
        return {
            "status": "success",
            "provider": provider,
            "message": f"{provider} portal closed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portal/status")
async def get_all_portal_status():
    """Get status of all provider portals."""
    try:
        from browser_portal import get_portal_manager, PORTAL_CONFIGS
        
        manager = get_portal_manager()
        active_portals = manager.get_active_portals()
        
        all_providers = []
        for provider in PORTAL_CONFIGS.keys():
            is_running = provider in active_portals
            config = PORTAL_CONFIGS[provider]
            all_providers.append({
                "provider": provider.value,
                "name": config.name,
                "is_running": is_running,
                "requires_login": config.requires_login,
                "url": config.url
            })
        
        return {
            "providers": all_providers,
            "active_count": len(active_portals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Browser Navigation Controls ---

@router.post("/portal/{provider}/back")
async def browser_go_back(provider: str):
    """Go back in browser history."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running")
        
        success = await portal.go_back()
        url = await portal.get_current_url()
        
        return {
            "status": "success" if success else "error",
            "provider": provider,
            "current_url": url,
            "message": "Navigated back" if success else "Could not go back"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal/{provider}/forward")
async def browser_go_forward(provider: str):
    """Go forward in browser history."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running")
        
        success = await portal.go_forward()
        url = await portal.get_current_url()
        
        return {
            "status": "success" if success else "error",
            "provider": provider,
            "current_url": url,
            "message": "Navigated forward" if success else "Could not go forward"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class NavigateRequest(BaseModel):
    url: str

@router.post("/portal/{provider}/navigate")
async def browser_navigate(provider: str, req: NavigateRequest):
    """Navigate to a specific URL."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running")
        
        success = await portal.goto_url(req.url)
        url = await portal.get_current_url()
        title = await portal.get_page_title()
        
        return {
            "status": "success" if success else "error",
            "provider": provider,
            "url": url,
            "title": title,
            "message": f"Navigated to {req.url}" if success else f"Failed to navigate to {req.url}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portal/{provider}/info")
async def get_browser_info(provider: str):
    """Get current browser page info (URL and title)."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail=f"{provider} portal not running")
        
        url = await portal.get_current_url()
        title = await portal.get_page_title()
        
        return {
            "status": "success",
            "provider": provider,
            "url": url,
            "title": title
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Proxy Management for Browser Portals ---

@router.post("/proxy/fetch")
async def fetch_new_proxies():
    """Fetch new free proxies and test them."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        
        # Fetch new proxies
        proxies = await proxy_mgr.fetch_proxies(limit=30)
        
        # Test first few to find a working one
        working_proxy = await proxy_mgr.get_working_proxy(max_attempts=5)
        
        stats = proxy_mgr.get_proxy_stats()
        
        return {
            "status": "success",
            "message": f"Fetched {len(proxies)} proxies",
            "working_proxy": str(working_proxy) if working_proxy else None,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxy/rotate")
async def rotate_proxy():
    """Rotate to a new working proxy."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        
        # Rotate to new proxy
        new_proxy = await proxy_mgr.rotate_proxy()
        
        if new_proxy:
            return {
                "status": "success",
                "proxy": str(new_proxy),
                "country": new_proxy.country,
                "response_time": f"{new_proxy.response_time:.2f}s"
            }
        else:
            raise HTTPException(status_code=503, detail="No working proxy available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proxy/status")
async def get_proxy_status():
    """Get current proxy status."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        
        stats = proxy_mgr.get_proxy_stats()
        current = proxy_mgr.get_current_proxy()
        
        return {
            "current_proxy": str(current) if current else None,
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxy/test")
async def test_current_proxy():
    """Test if current proxy is working."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        current = proxy_mgr.get_current_proxy()
        
        if not current:
            raise HTTPException(status_code=400, detail="No proxy currently set")
        
        is_working = await proxy_mgr.test_proxy(current)
        
        return {
            "status": "success",
            "proxy": str(current),
            "is_working": is_working,
            "response_time": f"{current.response_time:.2f}s" if is_working else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal/{provider}/restart-with-proxy")
async def restart_portal_with_proxy(provider: str):
    """Restart portal with current proxy."""
    try:
        from browser_portal import get_portal_manager, PortalProvider
        from proxy_manager import get_proxy_manager
        
        prov = PortalProvider(provider.lower())
        portal = get_portal_manager().get_portal(prov)
        proxy_mgr = get_proxy_manager()
        
        # Get current proxy
        current_proxy = proxy_mgr.get_current_proxy()
        if not current_proxy:
            raise HTTPException(status_code=503, detail="No custom proxy configured. Set one first.")
        
        # Close existing portal
        await portal.close()
        
        # Reinitialize with proxy
        await portal.initialize(headless=True, proxy=current_proxy)
        
        return {
            "status": "success",
            "provider": provider,
            "proxy": str(current_proxy),
            "message": f"{provider} portal restarted with proxy {current_proxy.ip}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Provider Toggle Management ---

class ProviderToggleRequest(BaseModel):
    provider_id: str
    enabled: bool

@router.get("/providers")
async def get_providers():
    """Get all providers with their enabled/disabled status."""
    try:
        from provider_state import get_provider_state_manager
        
        manager = await get_provider_state_manager()
        providers = manager.get_all_providers()
        
        return {
            "providers": [
                {
                    "id": provider_id,
                    "name": config["name"],
                    "type": config["type"],
                    "enabled": config["enabled"]
                }
                for provider_id, config in providers.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/providers/toggle")
async def toggle_provider(req: ProviderToggleRequest):
    """Enable or disable a provider."""
    try:
        from provider_state import get_provider_state_manager
        
        manager = await get_provider_state_manager()
        success = await manager.set_provider_state(req.provider_id, req.enabled)
        
        if success:
            return {
                "status": "success",
                "provider_id": req.provider_id,
                "enabled": req.enabled,
                "message": f"Provider '{req.provider_id}' {'enabled' if req.enabled else 'disabled'}"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to toggle provider '{req.provider_id}'")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Custom Proxy Management ---

class SetProxyRequest(BaseModel):
    proxy: str  # Format: ip:port or protocol://ip:port or protocol://user:pass@ip:port
    username: Optional[str] = None  # Optional username for proxy auth
    password: Optional[str] = None  # Optional password for proxy auth

@router.post("/proxy/set")
async def set_custom_proxy(req: SetProxyRequest):
    """Set a custom proxy for the entire container with optional authentication."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        success = proxy_mgr.set_custom_proxy(req.proxy, req.username, req.password)
        
        if success:
            status = proxy_mgr.get_status()
            return {
                "status": "success",
                "proxy": status["proxy"],
                "has_auth": status.get("has_auth", False),
                "username": status.get("username"),
                "message": "Custom proxy set successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid proxy format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxy/clear")
async def clear_custom_proxy():
    """Clear the custom proxy."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        proxy_mgr.clear_proxy()
        
        return {
            "status": "success",
            "message": "Custom proxy cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proxy/status")
async def get_proxy_status():
    """Get current proxy status."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        status = proxy_mgr.get_status()
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxy/test")
async def test_custom_proxy():
    """Test if the current custom proxy is working."""
    try:
        from proxy_manager import get_proxy_manager
        
        proxy_mgr = get_proxy_manager()
        
        if not proxy_mgr.get_current_proxy():
            raise HTTPException(status_code=400, detail="No custom proxy configured")
        
        is_working = await proxy_mgr.test_proxy()
        status = proxy_mgr.get_status()
        
        return {
            "status": "success",
            "is_working": is_working,
            **status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Saved Proxies Management ---

class ProxyCreateRequest(BaseModel):
    name: Optional[str] = None
    ip: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None

@router.get("/proxies")
async def list_proxies():
    """Get all saved proxies from Supabase."""
    try:
        from db import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            return {"proxies": []}
        
        res = supabase.table("kaiapi_proxies").select("*").order("created_at", desc=True).execute()
        return {"proxies": res.data or []}
    except Exception as e:
        logger.error(f"Failed to list proxies: {e}")
        return {"proxies": []}

@router.post("/terminal/sync-auth")
async def sync_terminal_auth(req: dict):
    """Sync OpenCode auth to Supabase."""
    try:
        from opencode_terminal import get_terminal_manager
        
        manager = get_terminal_manager()
        # Just use the default model to get an instance
        portal = manager.get_portal("opencode-kimi-k2.5-free") 
        success = await portal.sync_auth()
        
        if success:
            return {"status": "success", "message": "Auth synced to Supabase"}
        else:
            return {"status": "error", "message": "Failed to sync auth (check logs)"}
            
    except Exception as e:
        logger.error(f"Error syncing auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proxies")
async def create_proxy(req: ProxyCreateRequest):
    """Add a new proxy to Supabase."""
    try:
        from db import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        proxy_data = {
            "name": req.name,
            "ip": req.ip,
            "port": req.port,
            "protocol": req.protocol,
            "username": req.username,
            "password": req.password,
            "country": req.country,
            "city": req.city,
            "notes": req.notes,
            "is_active": False
        }
        
        res = supabase.table("kaiapi_proxies").insert(proxy_data).execute()
        
        return {
            "status": "success",
            "message": "Proxy saved",
            "proxy": res.data[0] if res.data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proxies/{proxy_id}/activate")
async def activate_proxy(proxy_id: int):
    """Activate a saved proxy."""
    try:
        from db import get_supabase
        from proxy_manager import get_proxy_manager
        
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        res = supabase.table("kaiapi_proxies").select("*").eq("id", proxy_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
        proxy = res.data[0]
        
        # Deactivate all first
        supabase.table("kaiapi_proxies").update({"is_active": False}).neq("id", proxy_id).execute()
        
        # Activate this one
        supabase.table("kaiapi_proxies").update({"is_active": True}).eq("id", proxy_id).execute()
        
        # Set as current
        proxy_mgr = get_proxy_manager()
        proxy_str = f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"
        proxy_mgr.set_custom_proxy(proxy_str, proxy.get("username"), proxy.get("password"))
        
        return {"status": "success", "message": f"Proxy activated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/proxies/{proxy_id}")
async def delete_proxy(proxy_id: int):
    """Delete a saved proxy."""
    try:
        from db import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        supabase.table("kaiapi_proxies").delete().eq("id", proxy_id).execute()
        
        return {"status": "success", "message": "Proxy deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- OpenCode Terminal Portal ---

class TerminalInput(BaseModel):
    text: str

class TerminalKey(BaseModel):
    key: str

@router.post("/terminal/start")
async def start_terminal(req: dict):
    """Start OpenCode terminal session."""
    try:
        from opencode_terminal import get_terminal_manager
        
        model = req.get("model", "kimi-k2.5-free")
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        if portal.is_running():
            return {
                "status": "already_running",
                "model": model,
                "message": f"Terminal for {model} is already running"
            }
        
        await portal.initialize()
        
        return {
            "status": "success",
            "model": model,
            "message": f"Terminal started for {model}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/terminal/output")
async def get_terminal_output(model: str = "kimi-k2.5-free", lines: int = 100):
    """Get recent terminal output."""
    try:
        from opencode_terminal import get_terminal_manager
        
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        if not portal.is_running():
            return {"lines": [], "status": "stopped"}
            
        output_lines = portal.get_output(max_lines=lines)
        
        # Format for frontend
        formatted_lines = [
            {"type": stream, "content": line} 
            for stream, line in output_lines
        ]
        
        return {
            "lines": formatted_lines,
            "status": "running"
        }
    except Exception as e:
        return {"lines": [], "error": str(e), "status": "error"}

@router.post("/terminal/input")
async def send_terminal_input(req: TerminalInput, model: str = "kimi-k2.5-free"):
    """Send text input to terminal."""
    try:
        from opencode_terminal import get_terminal_manager
        
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail="Terminal not running")
            
        success = await portal.send_input(req.text)
        
        return {"status": "success" if success else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/terminal/key")
async def send_terminal_key(req: TerminalKey, model: str = "kimi-k2.5-free"):
    """Send special key to terminal."""
    try:
        from opencode_terminal import get_terminal_manager
        
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail="Terminal not running")
            
        success = await portal.send_key(req.key)
        
        return {"status": "success" if success else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/terminal/close")
async def close_terminal(req: dict):
    """Close terminal session."""
    try:
        from opencode_terminal import get_terminal_manager
        
        model = req.get("model", "kimi-k2.5-free")
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        await portal.close()
        
        return {"status": "success", "message": "Terminal closed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/terminal/reset")
async def reset_terminal(req: dict):
    """Manually trigger a full disposable reset (wipes all traces and starts fresh)."""
    try:
        from opencode_terminal import get_terminal_manager
        
        model = req.get("model", "kimi-k2.5-free")
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        if not portal.is_running():
            raise HTTPException(status_code=400, detail="Terminal not running")
        
        success = await portal.manual_reset()
        
        return {
            "status": "success" if success else "error",
            "message": "Full disposable reset completed - OpenCode sees a brand new device!",
            "model": model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/terminal/status")
async def get_terminal_status(model: str = "kimi-k2.5-free"):
    """Get disposable mode status and message count."""
    try:
        from opencode_terminal import get_terminal_manager
        
        manager = get_terminal_manager()
        portal = manager.get_portal(model)
        
        status = portal.get_disposable_status()
        
        return {
            "status": "success",
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

