# TODO : ADD PPTX SUPPOURT

# app/services/presentation.py
import io
import base64
import fitz # PyMuPDF
# from pptx import Presentation # Keep for future PPTX support
import logging
import asyncio # Add asyncio import
from typing import List, Dict

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
        """Convert PDF pages to base64 encoded images (using executor)."""
        loop = asyncio.get_running_loop()
        try:
            # Run the potentially blocking PDF processing in a thread pool executor
            image_data = await loop.run_in_executor(None, self._sync_process_pdf, file_content)
            return image_data
        except Exception as e:
            logger.error(f"Async wrapper caught error during PDF processing: {e}")
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