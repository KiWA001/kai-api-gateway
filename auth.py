"""Authentication Module."""

from fastapi import Request, Header
from typing import Optional

async def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    return {
        "id": "open",
        "name": "Open Access",
        "limit_tokens": -1,
        "is_dashboard": True,
        "auth_ignored": True,
    }
