"""
Unified Provider Session Manager (Supabase)
--------------------------------------------
Manages persistent browser sessions for all providers via Supabase.
This ensures sessions survive redeploys and restarts.

Providers supported:
- huggingchat
- zai
- gemini
- (add more as needed)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("kai_api.provider_sessions")

# Session limits per provider
DEFAULT_MAX_CONVERSATIONS = {
    "huggingchat": 50,
    "zai": 100,
    "gemini": 100,
    "copilot": 999999,  # Unlimited for Copilot
}

# Session duration per provider (hours)
DEFAULT_SESSION_DURATION = {
    "huggingchat": 24,
    "zai": 48,
    "gemini": 48,
    "copilot": 720,  # 30 days for Copilot
}


class ProviderSessionManager:
    """Manages provider sessions via Supabase."""
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("✅ ProviderSessionManager: Connected to Supabase")
        except Exception as e:
            logger.error(f"❌ ProviderSessionManager: Failed to connect to Supabase: {e}")
    
    def is_available(self) -> bool:
        """Check if Supabase connection is available."""
        return self.supabase is not None
    
    def get_session(self, provider: str) -> Optional[Dict[str, Any]]:
        """
        Get session data for a provider.
        Returns None if no session or session expired.
        """
        if not self.supabase:
            return None
        
        try:
            response = self.supabase.table("kaiapi_provider_sessions").select("*").eq("provider", provider).execute()
            
            if not response.data:
                return None
            
            session = response.data[0]
            
            # Check if expired
            expires_at = session.get("expires_at")
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.now().astimezone() > expires_dt:
                    logger.info(f"Session for {provider} expired")
                    self.delete_session(provider)
                    return None
            
            # Check if exceeded max conversations
            conv_count = session.get("conversation_count", 0)
            max_conv = session.get("max_conversations", DEFAULT_MAX_CONVERSATIONS.get(provider, 50))
            if conv_count >= max_conv:
                logger.info(f"Session for {provider} reached {max_conv} conversations")
                self.delete_session(provider)
                return None
            
            logger.info(f"✅ Found valid session for {provider} ({conv_count}/{max_conv} conversations)")
            return session
            
        except Exception as e:
            logger.error(f"Failed to get session for {provider}: {e}")
            return None
    
    def save_session(
        self, 
        provider: str, 
        cookies: List[Dict], 
        conversation_count: int = 0,
        extra_data: Optional[Dict] = None
    ) -> bool:
        """
        Save session data for a provider.
        """
        if not self.supabase:
            logger.warning("Supabase not available, cannot save session")
            return False
        
        try:
            # Build session data
            session_data = {
                "cookies": cookies,
            }
            if extra_data:
                session_data.update(extra_data)
            
            # Calculate expiration
            duration_hours = DEFAULT_SESSION_DURATION.get(provider, 24)
            expires_at = datetime.now().astimezone() + timedelta(hours=duration_hours)
            
            # Get max conversations
            max_conv = DEFAULT_MAX_CONVERSATIONS.get(provider, 50)
            
            # Upsert using the stored function
            result = self.supabase.rpc(
                "upsert_provider_session",
                {
                    "p_provider": provider,
                    "p_session_data": session_data,
                    "p_conversation_count": conversation_count,
                    "p_max_conversations": max_conv,
                    "p_expires_at": expires_at.isoformat()
                }
            ).execute()
            
            logger.info(f"✅ Saved session for {provider} (expires: {expires_at})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session for {provider}: {e}")
            return False
    
    def increment_conversation(self, provider: str) -> bool:
        """
        Increment conversation count for a provider.
        """
        if not self.supabase:
            return False
        
        try:
            self.supabase.rpc(
                "increment_conversation_count",
                {"p_provider": provider}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to increment conversation for {provider}: {e}")
            return False
    
    def delete_session(self, provider: str) -> bool:
        """
        Delete session for a provider.
        """
        if not self.supabase:
            return False
        
        try:
            self.supabase.table("kaiapi_provider_sessions").delete().eq("provider", provider).execute()
            logger.info(f"Deleted session for {provider}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session for {provider}: {e}")
            return False
    
    def clear_all_sessions(self) -> bool:
        """
        Clear all provider sessions.
        """
        if not self.supabase:
            return False
        
        try:
            self.supabase.table("kaiapi_provider_sessions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info("Cleared all provider sessions")
            return True
        except Exception as e:
            logger.error(f"Failed to clear sessions: {e}")
            return False
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions.
        """
        if not self.supabase:
            return []
        
        try:
            response = self.supabase.table("kaiapi_provider_sessions").select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to get all sessions: {e}")
            return []
    
    def needs_login(self, provider: str) -> bool:
        """
        Check if provider needs login (no valid session).
        """
        session = self.get_session(provider)
        return session is None


# Global instance
_session_manager: Optional[ProviderSessionManager] = None


def get_provider_session_manager() -> ProviderSessionManager:
    """Get the global provider session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = ProviderSessionManager()
    return _session_manager
