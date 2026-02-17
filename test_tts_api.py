#!/usr/bin/env python3
"""
Test Script for SpeechMA TTS API
--------------------------------
Example usage of the 11Labs-compatible TTS endpoints.
"""

import requests
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your API URL
API_KEY = "your-api-key-here"  # Your KAI API key


def test_list_voices():
    """Test listing available voices."""
    print("\n🎙️  Testing: List Voices")
    print("-" * 50)
    
    response = requests.get(
        f"{BASE_URL}/v1/voices",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data['voices'])} voices")
        
        # Print first 5 voices
        for voice in data['voices'][:5]:
            print(f"  - {voice['voice_id']}: {voice['name']}")
            if voice.get('labels'):
                print(f"    Gender: {voice['labels'].get('gender', 'N/A')}, "
                      f"Accent: {voice['labels'].get('accent', 'N/A')}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def test_list_models():
    """Test listing TTS models."""
    print("\n🤖 Testing: List Models")
    print("-" * 50)
    
    response = requests.get(
        f"{BASE_URL}/v1/models",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data['models'])} models")
        for model in data['models']:
            print(f"  - {model['model_id']}: {model['name']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def test_get_voice(voice_id: str = "ava"):
    """Test getting a specific voice."""
    print(f"\n🎭 Testing: Get Voice '{voice_id}'")
    print("-" * 50)
    
    response = requests.get(
        f"{BASE_URL}/v1/voices/{voice_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        voice = response.json()
        print(f"✅ Found voice: {voice['name']}")
        print(f"   Category: {voice['category']}")
        if voice.get('labels'):
            print(f"   Labels: {voice['labels']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def test_text_to_speech(voice_id: str = "ava", text: str = "Hello, this is a test."):
    """Test text-to-speech conversion."""
    print(f"\n🔊 Testing: Text-to-Speech with '{voice_id}'")
    print("-" * 50)
    print(f"Text: {text}")
    
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/text-to-speech/{voice_id}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload
    )
    
    if response.status_code == 200:
        # Save audio file
        output_file = f"test_output_{voice_id}.mp3"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        file_size = len(response.content)
        print(f"✅ Success! Saved to {output_file}")
        print(f"   File size: {file_size:,} bytes")
        
        # Show headers
        if 'X-Character-Count' in response.headers:
            print(f"   Character count: {response.headers['X-Character-Count']}")
        if 'Request-Id' in response.headers:
            print(f"   Request ID: {response.headers['Request-Id']}")
        
        return output_file
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return None


def test_speechma_direct(text: str = "Hello from SpeechMA direct API.", voice_id: str = "ava"):
    """Test the direct SpeechMA endpoint with more options."""
    print(f"\n🎯 Testing: SpeechMA Direct API")
    print("-" * 50)
    print(f"Text: {text}")
    print(f"Voice: {voice_id}")
    
    payload = {
        "text": text,
        "voice_id": voice_id,
        "pitch": 0,
        "speed": 0,
        "volume": 100
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/tts/speechma",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload
    )
    
    if response.status_code == 200:
        output_file = f"test_speechma_direct_{voice_id}.mp3"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        file_size = len(response.content)
        print(f"✅ Success! Saved to {output_file}")
        print(f"   File size: {file_size:,} bytes")
        
        if 'X-Voice-Used' in response.headers:
            print(f"   Voice used: {response.headers['X-Voice-Used']}")
        
        return output_file
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return None


def test_speechma_voices():
    """Test getting SpeechMA-specific voice list."""
    print("\n🎙️  Testing: SpeechMA Voices List")
    print("-" * 50)
    
    response = requests.get(
        f"{BASE_URL}/v1/tts/speechma/voices",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['count']} voices")
        print(f"   Default: {data['default_voice']}")
        
        # Print all voices
        print("\n   Available Voices:")
        for voice in data['voices'][:10]:  # First 10
            print(f"   - {voice['voice_id']}: {voice['name']} ({voice['gender']}, {voice['country']})")
        
        if data['count'] > 10:
            print(f"   ... and {data['count'] - 10} more")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def test_health():
    """Test TTS health check."""
    print("\n🏥 Testing: Health Check")
    print("-" * 50)
    
    response = requests.get(f"{BASE_URL}/v1/tts/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"   Provider: {data['provider']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def test_user_subscription():
    """Test user subscription endpoint."""
    print("\n👤 Testing: User Subscription")
    print("-" * 50)
    
    response = requests.get(
        f"{BASE_URL}/v1/user/subscription",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Tier: {data['tier']}")
        print(f"   Character limit: {data['character_limit']:,}")
        print(f"   Character used: {data['character_count']:,}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 SpeechMA TTS API Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    
    # Health check first
    test_health()
    
    # List resources
    test_list_models()
    test_list_voices()
    test_speechma_voices()
    
    # Get specific voice
    test_get_voice("ava")
    test_get_voice("andrew")
    
    # User info
    test_user_subscription()
    
    # TTS generation (comment out if you don't want to generate audio)
    print("\n" + "=" * 60)
    print("🎵 Generating Audio Samples...")
    print("=" * 60)
    
    # Test different voices
    test_text_to_speech("ava", "Hello! I am Ava, a multilingual voice.")
    test_text_to_speech("andrew", "Greetings! I am Andrew, ready to help you.")
    test_text_to_speech("emma", "Hi there! I'm Emma with a British accent.")
    
    # Test direct API with effects
    test_speechma_direct(
        "This is a test with custom voice settings.",
        "brian"
    )
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
