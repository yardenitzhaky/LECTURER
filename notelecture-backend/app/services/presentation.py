# TODO : ADD PPTX SUPPOURT

# app/services/presentation.py
import io
import base64
from pathlib import Path
import fitz  # PyMuPDF for PDF processing
from pptx import Presentation
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class PresentationService:
    async def process_presentation(self, file_content: bytes, file_extension: str) -> List[str]:
        """Process presentation content and return list of base64 encoded images."""
        try:
            if file_extension.lower() in ['ppt', 'pptx']:
                return await self._process_powerpoint(file_content)
            elif file_extension.lower() == 'pdf':
                return await self._process_pdf(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
        except Exception as e:
            logger.error(f"Error processing presentation: {str(e)}")
            raise

    async def _process_pdf(self, file_content: bytes) -> List[str]:
        """Convert PDF pages to base64 encoded images."""
        image_data = []
        
        # Create a memory buffer for the PDF
        memory_buffer = io.BytesIO(file_content)
        pdf_document = fitz.open(stream=memory_buffer, filetype="pdf")
        
        try:
            for page_number in range(pdf_document.page_count):
                # Get the page
                page = pdf_document[page_number]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                
                # Convert to PNG in memory
                img_bytes = pix.tobytes("png")
                
                # Convert to base64
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                image_data.append(f"data:image/png;base64,{base64_image}")
                
        finally:
            pdf_document.close()
            memory_buffer.close()
            
        return image_data