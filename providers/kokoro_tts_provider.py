"""
Kokoro TTS Provider
-------------------
Fast, natural-sounding text-to-speech using Kokoro-82M model.
No browser automation, no CAPTCHA, runs locally.

Installation:
    pip install kokoro soundfile
    
Note: Requires espeak-ng for some languages:
    - Ubuntu/Debian: apt-get install espeak-ng
    - macOS: brew install espeak-ng
"""

import io
import logging
from typing import Optional
import asyncio

logger = logging.getLogger("kai_api.kokoro_tts")

# Try to import Kokoro
try:
    from kokoro import KPipeline
    import soundfile as sf
    import torch
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    logger.warning("Kokoro not installed. Run: pip install kokoro soundfile")


# Voice mapping - Kokoro uses codes like 'af_heart', 'am_michael', etc.
# Format: lang_code_voice (e.g., 'af' = American Female, 'am' = American Male)
KOKORO_VOICES = {
    # American English - Female
    "bella": {"code": "af_heart", "lang": "a", "gender": "Female", "accent": "American"},
    "sarah": {"code": "af_heart", "lang": "a", "gender": "Female", "accent": "American"},
    # American English - Male  
    "michael": {"code": "am_michael", "lang": "a", "gender": "Male", "accent": "American"},
    "adam": {"code": "am_michael", "lang": "a", "gender": "Male", "accent": "American"},
    # British English - Female
    "emma": {"code": "bf_emma", "lang": "b", "gender": "Female", "accent": "British"},
    # British English - Male
    "george": {"code": "bm_george", "lang": "b", "gender": "Male", "accent": "British"},
    # Spanish
    "sofia": {"code": "ef_sofia", "lang": "e", "gender": "Female", "accent": "Spanish"},
    # French
    "jean": {"code": "ff_jean", "lang": "f", "gender": "Male", "accent": "French"},
    # Japanese
    "sakura": {"code": "jf_sakura", "lang": "j", "gender": "Female", "accent": "Japanese"},
    # Chinese
    "li": {"code": "zf_li", "lang": "z", "gender": "Female", "accent": "Chinese"},
}

# Default voice
DEFAULT_VOICE = "bella"

# Cache pipelines per language to avoid reloading
_pipeline_cache = {}


class KokoroTTSProvider:
    """Kokoro Text-to-Speech Provider - Fast, natural, no browser needed."""
    
    def __init__(self):
        self.name = "kokoro"
        
    @staticmethod
    def is_available() -> bool:
        """Check if Kokoro is installed and working."""
        if not KOKORO_AVAILABLE:
            return False
        try:
            # Try to initialize a pipeline
            _ = KPipeline(lang_code='a')
            return True
        except Exception as e:
            logger.error(f"Kokoro initialization failed: {e}")
            return False
    
    def get_available_voices(self) -> list[dict]:
        """Return all available voices."""
        voices = []
        for voice_id, info in KOKORO_VOICES.items():
            voices.append({
                "voice_id": voice_id,
                "name": voice_id.capitalize(),
                "gender": info["gender"],
                "language": info["lang"],
                "accent": info["accent"],
                "kokoro_code": info["code"]
            })
        return voices
    
    def get_voice_info(self, voice_id: str) -> dict:
        """Get voice information by voice_id."""
        voice_id_lower = voice_id.lower()
        
        # Try direct match
        if voice_id_lower in KOKORO_VOICES:
            info = KOKORO_VOICES[voice_id_lower]
            return {
                "voice_id": voice_id_lower,
                "name": voice_id_lower.capitalize(),
                **info
            }
        
        # Try to find by partial match
        for vid, info in KOKORO_VOICES.items():
            if voice_id_lower in vid:
                return {
                    "voice_id": vid,
                    "name": vid.capitalize(),
                    **info
                }
        
        # Return default
        default_info = KOKORO_VOICES[DEFAULT_VOICE]
        return {
            "voice_id": DEFAULT_VOICE,
            "name": DEFAULT_VOICE.capitalize(),
            **default_info
        }
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = "bella",
        speed: float = 1.0,
    ) -> Optional[bytes]:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert (Kokoro works best with sentences)
            voice_id: Voice to use
            speed: Speech speed (0.5 to 2.0)
            
        Returns:
            MP3 audio data as bytes
        """
        if not KOKORO_AVAILABLE:
            raise RuntimeError("Kokoro not installed. Run: pip install kokoro soundfile")
        
        # Get voice info
        voice_info = self.get_voice_info(voice_id)
        kokoro_voice = voice_info["kokoro_code"]
        lang_code = voice_info["language"]
        
        logger.info(f"Kokoro TTS: voice={voice_info['voice_id']}, lang={lang_code}")
        
        # Use thread pool for CPU-intensive TTS (Kokoro is CPU-based)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._generate_sync, 
            text, 
            kokoro_voice, 
            lang_code,
            speed
        )
    
    def _generate_sync(
        self, 
        text: str, 
        voice: str, 
        lang_code: str,
        speed: float
    ) -> bytes:
        """Synchronous generation (runs in thread pool)."""
        try:
            # Get or create pipeline for this language
            if lang_code not in _pipeline_cache:
                logger.info(f"Initializing Kokoro pipeline for language: {lang_code}")
                _pipeline_cache[lang_code] = KPipeline(lang_code=lang_code)
            
            pipeline = _pipeline_cache[lang_code]
            
            # Generate audio
            generator = pipeline(text, voice=voice, speed=speed)
            
            # Collect all audio segments
            audio_segments = []
            for i, (gs, ps, audio) in enumerate(generator):
                audio_segments.append(audio)
                logger.debug(f"Generated segment {i}: {len(audio)} samples")
            
            if not audio_segments:
                raise ValueError("No audio generated")
            
            # Concatenate all segments
            import numpy as np
            full_audio = np.concatenate(audio_segments)
            
            # Convert to MP3 bytes
            buffer = io.BytesIO()
            sf.write(buffer, full_audio, 24000, format='MP3')
            buffer.seek(0)
            
            audio_bytes = buffer.getvalue()
            logger.info(f"Kokoro: Generated {len(audio_bytes)} bytes of MP3 audio")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Kokoro generation error: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if Kokoro is working."""
        if not KOKORO_AVAILABLE:
            return False
        try:
            # Quick test
            test_pipeline = KPipeline(lang_code='a')
            return True
        except:
            return False


# Global provider instance
_kokoro_provider = None

def get_kokoro_provider() -> KokoroTTSProvider:
    """Get or create the Kokoro provider singleton."""
    global _kokoro_provider
    if _kokoro_provider is None:
        _kokoro_provider = KokoroTTSProvider()
    return _kokoro_provider
