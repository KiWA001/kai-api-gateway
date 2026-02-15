"""
Provider State Manager
----------------------
Manages enabled/disabled state of providers with Supabase persistence.
Uses KAIAPI_ prefixed table names for multi-project organization.
"""

import logging
from typing import Dict, Optional
from db import get_supabase
from config import PROVIDERS

logger = logging.getLogger("kai_api.provider_state")

# Table name with KAIAPI_ prefix
TABLE_NAME = "KAIAPI_provider_states"

class ProviderStateManager:
    """Manages provider enable/disable state with Supabase persistence."""
    
    def __init__(self):
        self._providers: Dict[str, dict] = {}
        self._initialized = False
    
    async def initialize(self):
        """Load provider states from Supabase or use defaults."""
        if self._initialized:
            return
        
        supabase = get_supabase()
        
        if supabase:
            try:
                # Try to load from Supabase (using KAIAPI_ prefixed table)
                res = supabase.table(TABLE_NAME).select("*").execute()
                
                if res.data:
                    # Load existing states
                    for row in res.data:
                        provider_id = row.get("provider_id")
                        if provider_id:
                            self._providers[provider_id] = {
                                "enabled": row.get("enabled", False),
                                "name": row.get("name", provider_id),
                                "type": row.get("type", "api"),
                            }
                    logger.info(f"✅ Loaded {len(self._providers)} provider states from Supabase")
                else:
                    # Initialize with defaults
                    await self._initialize_defaults(supabase)
                    
            except Exception as e:
                logger.error(f"❌ Failed to load provider states: {e}")
                # Fall back to defaults
                self._providers = PROVIDERS.copy()
        else:
            # No Supabase, use defaults
            self._providers = PROVIDERS.copy()
        
        self._initialized = True
    
    async def _initialize_defaults(self, supabase):
        """Initialize provider states with defaults in Supabase."""
        for provider_id, config in PROVIDERS.items():
            self._providers[provider_id] = config.copy()
            
            try:
                supabase.table(TABLE_NAME).insert({
                    "provider_id": provider_id,
                    "enabled": config["enabled"],
                    "name": config["name"],
                    "type": config["type"]
                }).execute()
            except Exception as e:
                logger.warning(f"Could not insert provider {provider_id}: {e}")
        
        logger.info(f"✅ Initialized {len(self._providers)} default provider states")
    
    def get_provider_state(self, provider_id: str) -> Optional[dict]:
        """Get state for a specific provider."""
        return self._providers.get(provider_id)
    
    def is_enabled(self, provider_id: str) -> bool:
        """Check if a provider is enabled."""
        provider = self._providers.get(provider_id)
        return provider.get("enabled", False) if provider else False
    
    def get_all_providers(self) -> Dict[str, dict]:
        """Get all provider states."""
        return self._providers.copy()
    
    def get_enabled_providers(self) -> Dict[str, dict]:
        """Get only enabled providers."""
        return {
            k: v for k, v in self._providers.items() 
            if v.get("enabled", False)
        }
    
    async def set_provider_state(self, provider_id: str, enabled: bool) -> bool:
        """Enable or disable a provider and persist to Supabase."""
        if provider_id not in self._providers:
            logger.error(f"Unknown provider: {provider_id}")
            return False
        
        # Update local state
        self._providers[provider_id]["enabled"] = enabled
        
        # Persist to Supabase
        supabase = get_supabase()
        if supabase:
            try:
                # Check if row exists
                res = supabase.table(TABLE_NAME).select("id").eq("provider_id", provider_id).execute()
                
                if res.data:
                    # Update existing
                    supabase.table(TABLE_NAME).update({
                        "enabled": enabled
                    }).eq("provider_id", provider_id).execute()
                else:
                    # Insert new
                    supabase.table(TABLE_NAME).insert({
                        "provider_id": provider_id,
                        "enabled": enabled,
                        "name": self._providers[provider_id]["name"],
                        "type": self._providers[provider_id]["type"]
                    }).execute()
                
                logger.info(f"✅ Provider '{provider_id}' {'enabled' if enabled else 'disabled'}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to persist provider state: {e}")
                return False
        
        return True
    
    def get_enabled_provider_ids(self) -> list:
        """Get list of enabled provider IDs."""
        return [
            provider_id 
            for provider_id, config in self._providers.items()
            if config.get("enabled", False)
        ]


# Global instance
_provider_state_manager: Optional[ProviderStateManager] = None

async def get_provider_state_manager() -> ProviderStateManager:
    """Get the global provider state manager."""
    global _provider_state_manager
    if _provider_state_manager is None:
        _provider_state_manager = ProviderStateManager()
        await _provider_state_manager.initialize()
    return _provider_state_manager

def get_provider_state_manager_sync() -> ProviderStateManager:
    """Get provider state manager without async (for sync contexts)."""
    global _provider_state_manager
    if _provider_state_manager is None:
        _provider_state_manager = ProviderStateManager()
        # Don't initialize here - just return the instance
    return _provider_state_manager
