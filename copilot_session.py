"""
Copilot Session Manager
-----------------------
Manages persistent browser sessions and cookies for Microsoft Copilot.
Unlike HuggingChat, this has NO conversation limit - sessions persist indefinitely.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger("kai_api.copilot_session")

# Storage file for Copilot session
SESSION_FILE = "/tmp/copilot_session.json"


class CopilotSessionManager:
    """Manages Copilot browser session persistence - unlimited conversations."""

    @staticmethod
    def save_cookies(cookies: list, user_agent: str = None) -> bool:
        """
        Save cookies from an authenticated session.
        
        Args:
            cookies: List of cookie dictionaries from Playwright
            user_agent: User agent string used during authentication
        
        Returns:
            bool: True if saved successfully
        """
        try:
            session_data = {
                "cookies": cookies,
                "user_agent": user_agent,
                "timestamp": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),  # 30 days
            }
            
            with open(SESSION_FILE, "w") as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"✅ Saved {len(cookies)} cookies for Copilot session")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Copilot cookies: {e}")
            return False

    @staticmethod
    def load_session() -> Optional[dict]:
        """
        Load saved session data if it exists and is not expired.
        
        Returns:
            dict with cookies and user_agent, or None if no valid session
        """
        try:
            if not os.path.exists(SESSION_FILE):
                return None
            
            with open(SESSION_FILE, "r") as f:
                session_data = json.load(f)
            
            # Check expiration (30 days)
            expires_at = datetime.fromisoformat(session_data.get("expires_at", "2000-01-01"))
            if datetime.now() > expires_at:
                logger.info("Copilot session expired, need re-authentication")
                return None
            
            logger.info(f"✅ Loaded Copilot session (expires: {expires_at})")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to load Copilot cookies: {e}")
            return None

    @staticmethod
    def clear_session() -> bool:
        """Clear the saved session."""
        try:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
                logger.info("✅ Cleared Copilot session")
            return True
        except Exception as e:
            logger.error(f"Failed to clear Copilot session: {e}")
            return False

    @staticmethod
    def has_valid_session() -> bool:
        """Check if we have a valid authenticated session."""
        session = CopilotSessionManager.load_session()
        return session is not None and len(session.get("cookies", [])) > 0

    @staticmethod
    def get_session_info() -> dict:
        """Get information about the current session."""
        session = CopilotSessionManager.load_session()
        
        if not session:
            return {
                "has_session": False,
                "message": "No session found. May need CAPTCHA verification.",
            }
        
        expires_at = datetime.fromisoformat(session.get("expires_at", "2000-01-01"))
        time_left = expires_at - datetime.now()
        
        return {
            "has_session": True,
            "expires_at": session.get("expires_at"),
            "days_remaining": max(0, time_left.days),
            "cookie_count": len(session.get("cookies", [])),
            "timestamp": session.get("timestamp"),
        }
