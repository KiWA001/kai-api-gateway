# SpeechMA TTS Provider - 11Labs Compatible API

This module adds text-to-speech capabilities to KAI API using [SpeechMA](https://speechma.com) as the backend provider. The API is designed to be compatible with ElevenLabs API structure.

## Features

- 🎙️ **20+ High-Quality Voices** (Ava, Andrew, Brian, Emma, and more)
- 🔐 **Automatic CAPTCHA Solving** with OCR
- 🌍 **Multilingual Support** (English, Spanish, French, German, Japanese, etc.)
- 📱 **11Labs API Compatible** - Drop-in replacement for ElevenLabs
- 🎛️ **Voice Effects** (pitch, speed, volume control)

## Installation

### Required Dependencies

```bash
# Core dependencies (already in your project)
pip install fastapi playwright

# OCR dependencies (for CAPTCHA solving)
pip install pytesseract pillow

# OR use EasyOCR (alternative)
pip install easyocr

# Install Playwright browsers
playwright install chromium
```

### System Dependencies

For **pytesseract**, install Tesseract OCR:

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

## API Endpoints

### 11Labs-Compatible Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/models` | GET | List available TTS models |
| `/v1/voices` | GET | List all voices |
| `/v1/voices/{voice_id}` | GET | Get voice details |
| `/v1/voices/{voice_id}/settings` | GET | Get voice settings |
| `/v1/text-to-speech/{voice_id}` | POST | Generate speech |
| `/v1/text-to-speech/{voice_id}/stream` | POST | Generate speech (streaming) |
| `/v1/user/subscription` | GET | Get subscription info |

### SpeechMA-Specific Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/tts/speechma` | POST | Direct SpeechMA TTS with custom options |
| `/v1/tts/speechma/voices` | GET | Get all SpeechMA voices |
| `/v1/tts/health` | GET | Check TTS service health |

## Usage Examples

### 1. List Available Voices

```bash
curl -X GET "http://localhost:8000/v1/voices" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "voices": [
    {
      "voice_id": "ava",
      "name": "Ava Multilingual",
      "category": "premade",
      "labels": {
        "accent": "United States",
        "description": "Female Multilingual voice",
        "gender": "female"
      }
    }
  ]
}
```

### 2. Generate Speech (11Labs Style)

```bash
curl -X POST "http://localhost:8000/v1/text-to-speech/ava" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello! This is a test of the SpeechMA TTS API.",
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
      "stability": 0.5,
      "similarity_boost": 0.75
    }
  }' \
  --output speech.mp3
```

### 3. Generate Speech (SpeechMA Direct)

```bash
curl -X POST "http://localhost:8000/v1/tts/speechma" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello with custom voice effects!",
    "voice_id": "ava",
    "pitch": 0,
    "speed": 0,
    "volume": 100
  }' \
  --output speech_custom.mp3
```

### 4. Python Client Example

```python
import requests

# Configuration
API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

# Generate speech
response = requests.post(
    f"{BASE_URL}/v1/text-to-speech/ava",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"text": "Hello, world!"}
)

# Save audio
with open("output.mp3", "wb") as f:
    f.write(response.content)

print("Audio saved!")
```

## Available Voices

### Default: Ava Multilingual

The default voice is **Ava Multilingual** - a high-quality female voice with multilingual capabilities.

### All Available Voices

| Voice ID | Name | Gender | Language | Country |
|----------|------|--------|----------|---------|
| `ava` | Ava Multilingual | Female | Multilingual | United States |
| `andrew` | Andrew Multilingual | Male | Multilingual | United States |
| `brian` | Brian Multilingual | Male | Multilingual | United States |
| `emma` | Emma Multilingual | Female | Multilingual | United Kingdom |
| `remy` | Remy Multilingual | Male | Multilingual | France |
| `vivienne` | Vivienne Multilingual | Female | Multilingual | United States |
| `daniel` | Daniel Multilingual | Male | Multilingual | United Kingdom |
| `serena` | Serena Multilingual | Female | Multilingual | United States |
| `matthew` | Matthew Multilingual | Male | Multilingual | United States |
| `jane` | Jane Multilingual | Female | Multilingual | United States |
| `alfonso` | Alfonso Multilingual | Male | Multilingual | Spain |
| `mario` | Mario Multilingual | Male | Multilingual | Italy |
| `klaus` | Klaus Multilingual | Male | Multilingual | Germany |
| `sakura` | Sakura Multilingual | Female | Multilingual | Japan |
| `xin` | Xin Multilingual | Female | Multilingual | China |
| `jose` | Jose Multilingual | Male | Multilingual | Brazil |
| `ines` | Ines Multilingual | Female | Multilingual | Portugal |
| `amira` | Amira Multilingual | Female | Multilingual | Saudi Arabia |
| `fatima` | Fatima Multilingual | Female | Multilingual | UAE |

## Voice Effects (Direct API Only)

When using the `/v1/tts/speechma` endpoint, you can customize:

- **pitch**: Voice pitch adjustment (-10 to 10)
- **speed**: Speech speed adjustment (-10 to 10)  
- **volume**: Volume percentage (0-200)

```json
{
  "text": "Custom voice settings",
  "voice_id": "ava",
  "pitch": 2,
  "speed": -1,
  "volume": 120
}
```

## CAPTCHA Handling

SpeechMA requires CAPTCHA verification. The provider automatically:

1. Extracts CAPTCHA images from the page
2. Uses OCR (Tesseract or EasyOCR) to read the 5-digit code
3. Enters the code and submits
4. If OCR fails, automatically refreshes the CAPTCHA and retries (up to 5 times)

### Manual CAPTCHA Solving (If OCR Fails)

If OCR consistently fails, you can:

1. Check the CAPTCHA image manually at https://speechma.com
2. Call the API with pre-solved CAPTCHA (future enhancement)
3. Ensure Tesseract is properly installed

## Testing

Run the test suite:

```bash
python test_tts_api.py
```

This will test:
- ✅ Health check
- ✅ List voices and models
- ✅ Get voice details
- ✅ Generate audio samples
- ✅ Direct SpeechMA API

## Limitations

1. **Character Limit**: Maximum 2000 characters per request
2. **Rate Limits**: Depends on SpeechMA's server capacity
3. **CAPTCHA**: May occasionally fail if OCR can't read the image
4. **Audio Format**: Returns MP3 only (output_format is for compatibility)

## Troubleshooting

### CAPTCHA Not Solving

1. **Install Tesseract OCR:**
   ```bash
   # macOS
   brew install tesseract
   
   # Ubuntu
   sudo apt-get install tesseract-ocr
   ```

2. **Try EasyOCR instead:**
   ```bash
   pip install easyocr
   ```

3. **Check browser automation:**
   ```bash
   playwright install chromium
   ```

### Audio Not Generating

1. Check SpeechMA is accessible: `GET /v1/tts/health`
2. Check Playwright is installed: `playwright install`
3. Try refreshing CAPTCHA manually on speechma.com

### Import Errors

```bash
# Install missing OCR libraries
pip install pytesseract pillow

# Or
pip install easyocr
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  API Client │────▶│  TTS Router  │────▶│ SpeechMA    │
│             │     │ (11Labs API) │     │ Provider    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                         ┌──────▼──────┐
                                         │  Playwright │
                                         │  Browser    │
                                         └──────┬──────┘
                                                │
                                         ┌──────▼──────┐
                                         │  OCR Utils  │
                                         │ (Tesseract/ │
                                         │  EasyOCR)   │
                                         └─────────────┘
```

## API Compatibility

This implementation aims to be compatible with ElevenLabs API v1:

- ✅ Text-to-Speech conversion
- ✅ Voice listing
- ✅ Voice details
- ✅ Model listing
- ✅ Subscription info (mock)
- ❌ Voice cloning (not supported by SpeechMA)
- ❌ Real-time streaming (returns complete file)
- ❌ Pronunciation dictionaries (ignored)
- ❐ Voice settings (stored but not fully applied)

## Credits

- **SpeechMA**: https://speechma.com - Free TTS service
- **ElevenLabs**: API structure inspiration
- **Tesseract OCR**: Open source OCR engine
- **EasyOCR**: Alternative OCR library

## License

This code is part of the KAI API project. Follow your project's license terms.
