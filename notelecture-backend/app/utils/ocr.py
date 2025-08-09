import base64
import logging
from io import BytesIO
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

def extract_text_from_base64_image(base64_image_data: str) -> str:
    """
    Extracts text from a base64-encoded image using OCR.
    
    Args:
        base64_image_data: Base64 encoded image string (with or without data URL prefix)
    
    Returns:
        Extracted text or empty string if OCR fails
    """
    try:
        # Remove data URL prefix if present (e.g., "data:image/png;base64,")
        if base64_image_data.startswith('data:'):
            base64_image_data = base64_image_data.split(',', 1)[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_image_data)
        
        # Open image with PIL
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if necessary (OCR works better with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text using tesseract
        # Use Hebrew and English languages for better accuracy
        extracted_text = pytesseract.image_to_string(image, lang='heb+eng')
        
        # Clean up the text
        cleaned_text = extracted_text.strip().replace('\n\n', '\n')
        
        logger.info(f"OCR extracted {len(cleaned_text)} characters from slide")
        return cleaned_text
        
    except Exception as e:
        logger.warning(f"OCR text extraction failed: {e}")
        return ""