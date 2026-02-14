"""
HuggingChat Session Manager
----------------------------
Manages persistent browser sessions and cookies for HuggingChat.
This allows reuse of authenticated sessions across multiple API calls,
reducing login emails and improving performance.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger("kai_api.huggingchat_session")

# Storage file for HuggingChat session
SESSION_FILE = "/tmp/huggingchat_session.json"
MAX_CONVERSATIONS_PER_SESSION = 50


class HuggingChatSessionManager:
    """Manages HuggingChat browser session persistence."""
    
    def __init__(self):
        self._cookies: list = []
        self._conversation_count: int = 0
        self._last_login: Optional[datetime] = None
        self._is_authenticated: bool = False
        self._load_session()

    def _load_session(self):
        """Load saved session data if it exists and is valid."""
        try:
            if not os.path.exists(SESSION_FILE):
                return
            
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
            
            # Check if session is expired (24 hours)
            expires_at = datetime.fromisoformat(data.get("expires_at", "2000-01-01"))
            if datetime.now() > expires_at:
                logger.info("HuggingChat session expired")
                return
            
            # Check conversation limit
            if data.get("conversation_count", 0) >= MAX_CONVERSATIONS_PER_SESSION:
                logger.info(f"HuggingChat session reached {MAX_CONVERSATIONS_PER_SESSION} conversations")
                return
            
            self._cookies = data.get("cookies", [])
            self._conversation_count = data.get("conversation_count", 0)
            self._last_login = datetime.fromisoformat(data.get("last_login", datetime.now().isoformat()))
            self._is_authenticated = True
            
            logger.info(f"✅ Loaded HuggingChat session (conversations: {self._conversation_count}, expires: {expires_at})")
            
        except Exception as e:
            logger.error(f"Failed to load HuggingChat session: {e}")

    def save_session(self):
        """Save current session data."""
        try:
            data = {
                "cookies": self._cookies,
                "conversation_count": self._conversation_count,
                "last_login": self._last_login.isoformat() if self._last_login else datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            }
            
            with open(SESSION_FILE, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"✅ Saved HuggingChat session ({self._conversation_count} conversations)")
            
        except Exception as e:
            logger.error(f"Failed to save HuggingChat session: {e}")

    def clear_session(self):
        """Clear the saved session."""
        try:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            self._cookies = []
            self._conversation_count = 0
            self._is_authenticated = False
            logger.info("✅ Cleared HuggingChat session")
        except Exception as e:
            logger.error(f"Failed to clear HuggingChat session: {e}")

    def needs_login(self) -> bool:
        """Check if we need to login again."""
        if not self._is_authenticated:
            return True
        if not self._cookies:
            return True
        if self._conversation_count >= MAX_CONVERSATIONS_PER_SESSION:
            logger.info(f"Session reached {MAX_CONVERSATIONS_PER_SESSION} conversations, re-login required")
            return True
        return False

    def get_cookies(self) -> list:
        """Get current cookies."""
        return self._cookies

    def set_cookies(self, cookies: list):
        """Set cookies after successful login."""
        self._cookies = cookies
        self._is_authenticated = True
        self._last_login = datetime.now()

    def increment_conversation(self):
        """Increment conversation counter."""
        self._conversation_count += 1
        self.save_session()

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "is_authenticated": self._is_authenticated,
            "conversation_count": self._conversation_count,
            "max_conversations": MAX_CONVERSATIONS_PER_SESSION,
            "cookies_count": len(self._cookies),
            "last_login": self._last_login.isoformat() if self._last_login else None,
            "needs_login": self.needs_login(),
        }


# Global session manager instance
_session_manager = HuggingChatSessionManager()


def get_session_manager() -> HuggingChatSessionManager:
    """Get the global session manager instance."""
    return _session_manager
