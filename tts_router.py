"""
TTS Router - 11Labs Compatible API
----------------------------------
Text-to-Speech endpoints compatible with ElevenLabs API structure.
Uses SpeechMA as the backend provider.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import time
import uuid
import json

from auth import verify_api_key
from providers.speechma_tts_provider import get_speechma_provider

router = APIRouter()


# --- Pydantic Models (11Labs Compatible) ---

class VoiceSettings(BaseModel):
    """Voice settings for TTS."""
    stability: float = Field(default=0.5, ge=0.0, le=1.0, description="Voice stability")
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0, description="Similarity boost")
    style: float = Field(default=0.0, ge=0.0, le=1.0, description="Style exaggeration")
    use_speaker_boost: bool = Field(default=True, description="Use speaker boost")


class TextToSpeechRequest(BaseModel):
    """11Labs-compatible TTS request."""
    text: str = Field(..., max_length=2000, description="Text to convert to speech")
    model_id: Optional[str] = Field("eleven_multilingual_v2", description="Model ID (ignored, uses SpeechMA)")
    voice_settings: Optional[VoiceSettings] = Field(None, description="Voice settings")
    pronunciation_dictionary_locators: Optional[List[Dict[str, str]]] = None
    seed: Optional[int] = None
    previous_text: Optional[str] = None
    language_code: Optional[str] = None
    
    # SpeechMA-specific fields
    voice_id: Optional[str] = Field("ava", description="Voice ID to use")
    output_format: Optional[str] = Field("mp3_44100_128", description="Output format")
    optimize_streaming_latency: Optional[int] = Field(0, ge=0, le=4)


class VoiceResponse(BaseModel):
    """Voice information response."""
    voice_id: str
    name: str
    samples: Optional[List[Dict[str, Any]]] = None
    category: str = "premade"
    fine_tuning: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None
    available_for_tiers: List[str] = ["free", "starter", "creator", "enterprise"]
    settings: Optional[VoiceSettings] = None
    sharing: Optional[Dict[str, Any]] = None
    high_quality_base_model_ids: Optional[List[str]] = None
    safety_control: Optional[str] = None
    voice_verification: Optional[Dict[str, Any]] = None
    permission_on_resource: Optional[str] = None
    is_legacy: bool = False
    is_mixed: bool = False


class VoicesListResponse(BaseModel):
    """List of voices response."""
    voices: List[VoiceResponse]


class TTSModelInfo(BaseModel):
    """TTS model information."""
    model_id: str
    name: str
    description: str
    can_do_text_to_speech: bool = True
    can_do_voice_conversion: bool = False
    can_use_style: bool = True
    can_use_speaker_boost: bool = True
    serves_pro_voices: bool = True
    serves_v2_models: bool = True
    token_cost_factor: float = 1.0
    requires_alpha_access: bool = False
    max_characters_request_free_user: int = 2000
    max_characters_request_subscribed_user: int = 2000
    languages: List[Dict[str, str]]


class TTSModelsResponse(BaseModel):
    """TTS models list response."""
    models: List[TTSModelInfo]


class UserSubscriptionResponse(BaseModel):
    """User subscription info (mock for compatibility)."""
    tier: str = "free"
    character_count: int = 0
    character_limit: int = 1000000
    can_extend_character_limit: bool = True
    allowed_to_extend_character_limit: bool = True
    next_character_count_reset_unix: int = 0
    voice_slots_used: int = 1
    voice_slots_available: int = 100
    professional_voice_slots_used: int = 0
    professional_voice_slots_available: int = 5
    can_use_delayed_payment_methods: bool = False
    can_use_instant_voice_cloning: bool = True
    can_use_professional_voice_cloning: bool = False
    currency: Dict[str, Any] = {"usd": "USD"}
    status: str = "active"
    has_open_invoices: bool = False


# --- Helper Functions ---

def format_voice_to_11labs(voice_id: str, voice_info: dict) -> VoiceResponse:
    """Convert SpeechMA voice to 11Labs format."""
    return VoiceResponse(
        voice_id=voice_id,
        name=voice_info["name"],
        category="premade",
        labels={
            "accent": voice_info.get("country", "Multilingual"),
            "description": f"{voice_info['gender']} {voice_info['language']} voice",
            "age": "adult",
            "gender": voice_info["gender"].lower(),
            "use_case": "general"
        },
        description=f"{voice_info['gender']} {voice_info['language']} voice from {voice_info.get('country', 'Unknown')}",
        settings=VoiceSettings()
    )


# --- Endpoints ---

@router.get("/v1/user/subscription", response_model=UserSubscriptionResponse)
async def get_user_subscription(
    key_data: dict = Depends(verify_api_key)
):
    """
    Get user subscription information.
    Mock endpoint for 11Labs compatibility.
    """
    return UserSubscriptionResponse(
        tier="free",
        character_count=0,
        character_limit=1000000,
        next_character_count_reset_unix=int(time.time()) + 86400 * 30
    )


@router.get("/v1/models", response_model=TTSModelsResponse)
async def list_tts_models(
    key_data: dict = Depends(verify_api_key)
):
    """
    List available TTS models.
    """
    models = [
        TTSModelInfo(
            model_id="eleven_multilingual_v2",
            name="Eleven Multilingual v2",
            description="Our most advanced multilingual model with highest quality",
            can_do_text_to_speech=True,
            can_do_voice_conversion=False,
            can_use_style=True,
            can_use_speaker_boost=True,
            serves_pro_voices=True,
            serves_v2_models=True,
            token_cost_factor=1.0,
            requires_alpha_access=False,
            max_characters_request_free_user=2000,
            max_characters_request_subscribed_user=2000,
            languages=[
                {"language_id": "en", "name": "English"},
                {"language_id": "es", "name": "Spanish"},
                {"language_id": "fr", "name": "French"},
                {"language_id": "de", "name": "German"},
                {"language_id": "it", "name": "Italian"},
                {"language_id": "pt", "name": "Portuguese"},
                {"language_id": "ja", "name": "Japanese"},
                {"language_id": "zh", "name": "Chinese"},
                {"language_id": "ar", "name": "Arabic"},
                {"language_id": "hi", "name": "Hindi"},
            ]
        ),
        TTSModelInfo(
            model_id="eleven_flash_v2_5",
            name="Eleven Flash v2.5",
            description="Ultra-low latency model (~75ms)",
            can_do_text_to_speech=True,
            can_do_voice_conversion=False,
            can_use_style=False,
            can_use_speaker_boost=True,
            serves_pro_voices=True,
            serves_v2_models=True,
            token_cost_factor=0.5,
            requires_alpha_access=False,
            max_characters_request_free_user=2000,
            max_characters_request_subscribed_user=2000,
            languages=[
                {"language_id": "en", "name": "English"},
                {"language_id": "es", "name": "Spanish"},
                {"language_id": "fr", "name": "French"},
            ]
        )
    ]
    
    return TTSModelsResponse(models=models)


@router.get("/v1/voices", response_model=VoicesListResponse)
async def list_voices(
    key_data: dict = Depends(verify_api_key)
):
    """
    List all available voices.
    """
    provider = get_speechma_provider()
    voices_data = provider.get_available_voices()
    
    voices = []
    for voice_data in voices_data:
        voice_id = voice_data["voice_id"]
        info = {
            "name": voice_data["name"],
            "gender": voice_data["gender"],
            "language": voice_data["language"],
            "country": voice_data.get("country", "Unknown")
        }
        voices.append(format_voice_to_11labs(voice_id, info))
    
    return VoicesListResponse(voices=voices)


@router.get("/v1/voices/{voice_id}", response_model=VoiceResponse)
async def get_voice(
    voice_id: str,
    key_data: dict = Depends(verify_api_key)
):
    """
    Get information about a specific voice.
    """
    provider = get_speechma_provider()
    voice_info = provider.get_voice_info(voice_id)
    
    if not voice_info:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    
    return format_voice_to_11labs(voice_info["voice_id"], {
        "name": voice_info["name"],
        "gender": voice_info["gender"],
        "language": voice_info["language"],
        "country": voice_info.get("country", "Unknown")
    })


@router.get("/v1/voices/{voice_id}/settings", response_model=VoiceSettings)
async def get_voice_settings(
    voice_id: str,
    key_data: dict = Depends(verify_api_key)
):
    """
    Get default settings for a voice.
    """
    provider = get_speechma_provider()
    voice_info = provider.get_voice_info(voice_id)
    
    if not voice_info:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    
    return VoiceSettings()


@router.post("/v1/text-to-speech/{voice_id}")
async def text_to_speech(
    voice_id: str,
    request: TextToSpeechRequest,
    key_data: dict = Depends(verify_api_key)
):
    """
    Convert text to speech.
    
    This endpoint is compatible with 11Labs API:
    POST /v1/text-to-speech/{voice_id}
    
    Returns audio data as MP3.
    """
    provider = get_speechma_provider()
    
    # Validate voice
    voice_info = provider.get_voice_info(voice_id)
    if not voice_info:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    
    # Use provided voice_id or from request
    actual_voice_id = voice_id
    
    # Generate speech
    try:
        audio_data = await provider.generate_speech(
            text=request.text,
            voice_id=actual_voice_id,
            output_format=request.output_format or "mp3"
        )
        
        if audio_data is None:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate speech. This could be due to CAPTCHA issues or site changes."
            )
        
        # Return audio with proper headers
        headers = {
            "Content-Type": "audio/mpeg",
            "X-Character-Count": str(len(request.text)),
            "Request-Id": f"tts-{uuid.uuid4().hex[:12]}"
        }
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Speech generation failed: {str(e)}"
        )


@router.post("/v1/text-to-speech/{voice_id}/stream")
async def text_to_speech_stream(
    voice_id: str,
    request: TextToSpeechRequest,
    key_data: dict = Depends(verify_api_key)
):
    """
    Convert text to speech with streaming response.
    
    Note: Since SpeechMA generates complete audio files, 
    this returns the full audio as a stream.
    """
    provider = get_speechma_provider()
    
    # Validate voice
    voice_info = provider.get_voice_info(voice_id)
    if not voice_info:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    
    try:
        audio_data = await provider.generate_speech(
            text=request.text,
            voice_id=voice_id,
            output_format=request.output_format or "mp3"
        )
        
        if audio_data is None:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate speech"
            )
        
        # Return as streaming response
        def audio_generator():
            # Yield audio data in chunks
            chunk_size = 8192
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i + chunk_size]
        
        headers = {
            "X-Character-Count": str(len(request.text)),
            "Request-Id": f"tts-stream-{uuid.uuid4().hex[:12]}"
        }
        
        return StreamingResponse(
            audio_generator(),
            media_type="audio/mpeg",
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Speech generation failed: {str(e)}"
        )


# Additional SpeechMA-specific endpoints

@router.post("/v1/tts/speechma")
async def speechma_tts(
    request: Request,
    key_data: dict = Depends(verify_api_key)
):
    """
    Direct SpeechMA TTS endpoint with custom options.
    
    Body: {
        "text": "Hello world",
        "voice_id": "ava",
        "pitch": 0,
        "speed": 0,
        "volume": 100
    }
    """
    data = await request.json()
    
    text = data.get("text")
    voice_id = data.get("voice_id", "ava")
    pitch = data.get("pitch", 0)
    speed = data.get("speed", 0)
    volume = data.get("volume", 100)
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Text exceeds 2000 character limit")
    
    provider = get_speechma_provider()
    
    # Validate voice
    voice_info = provider.get_voice_info(voice_id)
    if not voice_info:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    
    try:
        audio_data = await provider.generate_speech(
            text=text,
            voice_id=voice_id,
            pitch=pitch,
            speed=speed,
            volume=volume
        )
        
        if audio_data is None:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate speech. This could be due to CAPTCHA issues."
            )
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="speech_{voice_id}.mp3"',
                "X-Voice-Used": voice_info["voice_id"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Speech generation failed: {str(e)}"
        )


@router.get("/v1/tts/speechma/voices")
async def speechma_voices(
    key_data: dict = Depends(verify_api_key)
):
    """
    Get all available SpeechMA voices with full details.
    """
    provider = get_speechma_provider()
    voices = provider.get_available_voices()
    
    return JSONResponse({
        "voices": voices,
        "count": len(voices),
        "default_voice": "ava"
    })


@router.get("/v1/tts/health")
async def tts_health_check():
    """
    Check if TTS service is healthy.
    """
    try:
        provider = get_speechma_provider()
        is_healthy = await provider.health_check()
        
        return JSONResponse({
            "status": "healthy" if is_healthy else "unhealthy",
            "provider": "speechma",
            "timestamp": time.time()
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "provider": "speechma",
            "error": str(e),
            "timestamp": time.time()
        }, status_code=503)
