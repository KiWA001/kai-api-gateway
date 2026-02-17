#!/usr/bin/env python3
"""
Test SpeechMA TTS locally to debug issues
"""

import asyncio
import sys
sys.path.insert(0, '/Users/mac/KAI_API')

from providers.speechma_tts_provider import SpeechMATTSProvider, get_speechma_provider

async def test_tts():
    """Test TTS generation locally."""
    print("🎙️  Testing SpeechMA TTS...\n")
    
    provider = get_speechma_provider()
    
    # Test 1: Check voices
    print("1. Available voices:")
    voices = provider.get_available_voices()
    for voice in voices[:5]:
        print(f"   - {voice['voice_id']}: {voice['name']}")
    print(f"   ... and {len(voices) - 5} more\n")
    
    # Test 2: Generate speech
    print("2. Generating speech with Ava...")
    print("   Text: 'Hello, this is a test of the text to speech system.'")
    print("   (This may take 30-60 seconds due to CAPTCHA solving)\n")
    
    try:
        audio_data = await provider.generate_speech(
            text="Hello, this is a test of the text to speech system.",
            voice_id="ava"
        )
        
        if audio_data:
            print(f"✅ SUCCESS! Generated {len(audio_data)} bytes of audio")
            
            # Save to file
            output_file = "/tmp/test_speech.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"✅ Saved to {output_file}")
            
            # Try to play it (macOS)
            import subprocess
            try:
                subprocess.run(["afplay", output_file], check=True)
                print("🔊 Playing audio...")
            except:
                print("📁 Audio saved but couldn't play automatically")
        else:
            print("❌ FAILED: No audio data returned")
            print("   This usually means CAPTCHA solving failed")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_tts())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test cancelled")
