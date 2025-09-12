# TODO : ADD PPTX SUPPOURT

# app/services/presentation.py
import io
import base64
import logging
import asyncio
import httpx
from typing import List, Dict
from app.core.config import settings

# Check if PyMuPDF is available
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    fitz = None
    logging.warning("PyMuPDF not available - will use external service for PDF processing")

logger = logging.getLogger(__name__)

class PresentationService:
    async def process_presentation(self, file_content: bytes, file_extension: str) -> List[str]:
        try:
            if file_extension.lower() in ['ppt', 'pptx']:
                # return await self._process_powerpoint(file_content) # Needs implementation
                logger.warning(f"PPT/PPTX processing not yet implemented for file extension: {file_extension}")
                raise NotImplementedError("PowerPoint processing is not yet supported.")
            elif file_extension.lower() == 'pdf':
                return await self._process_pdf(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
        except Exception as e:
            logger.error(f"Error processing presentation: {str(e)}")
            raise

    # --- Synchronous Helper for _process_pdf ---
    def _sync_process_pdf(self, file_content: bytes) -> List[str]:
        """Synchronous part of PDF processing."""
        image_data_list = []
        try:
            # Create a memory buffer for the PDF
            memory_buffer = io.BytesIO(file_content)
            pdf_document = fitz.open(stream=memory_buffer, filetype="pdf")

            for page_number in range(pdf_document.page_count):
                page = pdf_document[page_number]
                # Render page to pixmap (potentially CPU intensive)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for quality
                # Convert to PNG in memory
                img_bytes = pix.tobytes("png")
                # Encode to base64
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                image_data_list.append(f"data:image/png;base64,{base64_image}")

            pdf_document.close()
            memory_buffer.close()
            logger.info(f"[Sync] Processed {len(image_data_list)} PDF pages into images.")
            return image_data_list

        except Exception as e:
             logger.error(f"[Sync] Error during PDF processing: {e}", exc_info=True)
             # Ensure resources are closed even on error
             if 'pdf_document' in locals() and pdf_document: pdf_document.close()
             if 'memory_buffer' in locals() and memory_buffer: memory_buffer.close()
             raise # Re-raise

    async def _process_pdf(self, file_content: bytes) -> List[str]:
        """Convert PDF pages to base64 encoded images (using external service if PyMuPDF not available)."""
        # Try external service first if PyMuPDF is not available or external service is configured
        if not FITZ_AVAILABLE or settings.EXTERNAL_SERVICE_URL:
            try:
                return await self._process_pdf_external(file_content)
            except Exception as e:
                logger.warning(f"External PDF processing failed: {e}")
                if not FITZ_AVAILABLE:
                    raise Exception("PDF processing is not available - please use external service")
        
        # Fallback to local processing if PyMuPDF is available
        if FITZ_AVAILABLE:
            loop = asyncio.get_running_loop()
            try:
                # Run the potentially blocking PDF processing in a thread pool executor
                image_data = await loop.run_in_executor(None, self._sync_process_pdf, file_content)
                return image_data
            except Exception as e:
                logger.error(f"Local PDF processing failed: {e}")
                raise
        else:
            raise Exception("PDF processing is not available - please use external service")

    async def _process_pdf_external(self, file_content: bytes) -> List[str]:
        """Process PDF using external service."""
        if not settings.EXTERNAL_SERVICE_URL:
            raise Exception("External service URL not configured")
        
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                files = {"file": ("presentation.pdf", file_content, "application/pdf")}
                headers = {}
                if settings.EXTERNAL_SERVICE_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.EXTERNAL_SERVICE_API_KEY}"
                
                response = await client.post(
                    f"{settings.EXTERNAL_SERVICE_URL}/process-pdf/",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Convert text slides to base64 images (simplified approach)
                # In production, you'd want the external service to return actual images
                slides_text = result.get("slides", [])
                logger.info(f"External service processed PDF into {len(slides_text)} text slides")
                
                # For now, return the text as-is. In production, convert to images
                return slides_text
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling external service: {e}")
            raise Exception(f"External PDF processing failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling external PDF service: {e}")
            raise

    # --- Placeholder for future PPTX processing ---
    # async def _process_powerpoint(self, file_content: bytes) -> List[str]:
    #     """Convert PowerPoint slides to base64 encoded images (needs implementation)."""
    #     # This would likely also need a sync helper and run_in_executor
    #     # using python-pptx and Pillow/Wand for image conversion.
    #     logger.warning("PowerPoint processing called but not implemented.")
    #     # Example sync helper structure:
    #     # def _sync_process_pptx(content):
    #     #    prs = Presentation(io.BytesIO(content))
    #     #    images = []
    #     #    for i, slide in enumerate(prs.slides):
    #     #        # Logic to export slide as image (this is the complex part,
    #     #        # might need intermediate saving or a library like aspose.slides)
    #     #        pass
    #     #    return images
    #     # loop = asyncio.get_running_loop()
    #     # images = await loop.run_in_executor(None, _sync_process_pptx, file_content)
    #     # return images
    #     return []