"""
OCR Utilities for CAPTCHA Solving
---------------------------------
Helper functions to solve CAPTCHA images from SpeechMA.
"""

import base64
import io
import re
from typing import Optional


async def extract_digits_from_image(image_data: bytes, method: str = "auto") -> Optional[str]:
    """
    Extract 5-digit CAPTCHA code from image.
    
    Args:
        image_data: Raw image bytes
        method: OCR method to use - "tesseract", "easyocr", or "auto"
        
    Returns:
        5-digit code or None if extraction failed
    """
    
    if method == "auto":
        # Try tesseract first, then easyocr
        result = await _try_tesseract(image_data)
        if result:
            return result
        return await _try_easyocr(image_data)
    
    elif method == "tesseract":
        return await _try_tesseract(image_data)
    
    elif method == "easyocr":
        return await _try_easyocr(image_data)
    
    return None


async def _try_tesseract(image_data: bytes) -> Optional[str]:
    """Try extracting digits using pytesseract."""
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Preprocess for better OCR
        # Convert to grayscale
        image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Denoise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Binarize
        threshold = 128
        image = image.point(lambda x: 0 if x < threshold else 255, '1')
        
        # OCR config optimized for single line of digits
        custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(image, config=custom_config)
        
        # Extract exactly 5 digits
        digits = re.findall(r'\d', text)
        if len(digits) >= 5:
            return ''.join(digits[:5])
        
        return None
        
    except ImportError:
        return None
    except Exception as e:
        print(f"Tesseract OCR error: {e}")
        return None


async def _try_easyocr(image_data: bytes) -> Optional[str]:
    """Try extracting digits using EasyOCR."""
    try:
        import easyocr
        import tempfile
        import os
        
        # EasyOCR requires a file path, so save temporarily
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name
        
        try:
            # Initialize reader (English only)
            reader = easyocr.Reader(['en'], gpu=False)
            
            # Read text
            results = reader.readtext(tmp_path)
            
            if results:
                # Get the text with highest confidence
                text = results[0][1]
                
                # Extract exactly 5 digits
                digits = re.findall(r'\d', text)
                if len(digits) >= 5:
                    return ''.join(digits[:5])
        
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        return None
        
    except ImportError:
        return None
    except Exception as e:
        print(f"EasyOCR error: {e}")
        return None


def preprocess_captcha_image(image_data: bytes) -> bytes:
    """
    Preprocess CAPTCHA image for better OCR results.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Preprocessed image bytes
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Sharpen
        image = image.filter(ImageFilter.SHARPEN)
        
        # Resize slightly larger for better OCR
        width, height = image.size
        image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
        
    except Exception as e:
        print(f"Image preprocessing error: {e}")
        return image_data


# Simple fallback digit recognition (very basic)
def simple_digit_recognition(image_data: bytes) -> Optional[str]:
    """
    Very simple fallback digit recognition.
    Not very accurate, but doesn't require external libraries.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Guessed 5-digit code or None
    """
    try:
        from PIL import Image
        
        image = Image.open(io.BytesIO(image_data))
        image = image.convert('L')
        
        # Get image dimensions
        width, height = image.size
        
        # Simple heuristic: Look for 5 vertical segments with high contrast
        # This is a very naive approach and won't work well for complex CAPTCHAs
        
        pixels = list(image.getdata())
        
        # Divide image into 5 equal vertical segments
        segment_width = width // 5
        digits = []
        
        for i in range(5):
            # Get center of each segment
            x = i * segment_width + segment_width // 2
            
            # Count dark pixels in this column
            dark_count = 0
            for y in range(height):
                idx = y * width + x
                if idx < len(pixels) and pixels[idx] < 128:
                    dark_count += 1
            
            # Simple classification based on darkness
            # This is extremely basic and won't work reliably
            darkness_ratio = dark_count / height
            
            # Guess digit based on darkness (very rough)
            if darkness_ratio < 0.1:
                digits.append('1')
            elif darkness_ratio < 0.2:
                digits.append('7')
            elif darkness_ratio < 0.3:
                digits.append('4')
            elif darkness_ratio < 0.4:
                digits.append('2')
            elif darkness_ratio < 0.5:
                digits.append('3')
            elif darkness_ratio < 0.6:
                digits.append('5')
            elif darkness_ratio < 0.7:
                digits.append('6')
            elif darkness_ratio < 0.8:
                digits.append('9')
            elif darkness_ratio < 0.9:
                digits.append('8')
            else:
                digits.append('0')
        
        return ''.join(digits)
        
    except Exception as e:
        print(f"Simple recognition error: {e}")
        return None
