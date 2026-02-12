"""
KAI_API Pydantic Models
-----------------------
Request and response schemas for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Request body for POST /chat"""
    message: str = Field(
        ...,
        description="The user's message/prompt to send to the AI",
        min_length=1,
        max_length=32000,
    )
    model: Optional[str] = Field(
        default=None,
        description="AI model to use (e.g., 'gpt-4o-mini'). Defaults to best available.",
    )
    provider: Optional[str] = Field(
        default="auto",
        description="Provider to use: 'auto', 'g4f', or 'pollinations'. If omitted, tries all.",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional system prompt to set the AI's behavior",
    )


class ChatResponse(BaseModel):
    """Response body for POST /chat"""
    response: str = Field(description="The AI-generated response")
    model: str = Field(description="The model that generated the response")
    provider: str = Field(description="The provider that handled the request")
    attempts: Optional[int] = Field(
        default=1,
        description="Number of model+provider combinations tried before success",
    )
    response_time_ms: Optional[float] = Field(
        default=None,
        description="Total response time in milliseconds",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="UTC timestamp of the response",
    )


class ErrorResponse(BaseModel):
    """Error response body"""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error info")


class ModelInfo(BaseModel):
    """Model information"""
    model: str
    provider: str


class ModelsResponse(BaseModel):
    """Response body for GET /models"""
    models: list[ModelInfo]
    total: int


class ProviderHealth(BaseModel):
    """Health status for a single provider"""
    provider: str
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response body for GET /health"""
    status: str  # "healthy", "degraded", "unhealthy"
    providers: list[ProviderHealth]
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
