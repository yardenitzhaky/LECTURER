# notelecture-backend/app/services/summarization.py
import logging
from openai import OpenAI, AsyncOpenAI
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self):
        self.client: AsyncOpenAI | None = None 
        if not settings.openai_api_key or settings.openai_api_key == "YOUR_OPENAI_API_KEY":
            logger.warning("OpenAI API Key not configured. Summarization will be skipped.")
        else:
            try:
                # 1. Explicitly create an httpx.AsyncClient instance
                custom_http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(60.0, connect=5.0) 
                )
                logger.info("Custom httpx.AsyncClient created.")

                # 2. Pass this pre-configured client to AsyncOpenAI
                self.client = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    http_client=custom_http_client
                )
                logger.info("AsyncOpenAI client initialized successfully using custom httpx client.")

            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                self.client = None 

    async def summarize_text(self, text: str, max_length: int = 75) -> str | None:
        """
        Generates a summary for the given text using OpenAI's API.
        Returns the summary string or None if summarization fails or is skipped.
        """
        if not self.client:
            logger.info("Skipping summarization as OpenAI client is not initialized.")
            return None
        if not text or text.strip() == "":
            logger.info("Skipping summarization for empty text.")
            return None

        # Truncate text if it's extremely long
        max_input_chars = 8000
        if len(text) > max_input_chars:
            logger.warning(f"Input text too long ({len(text)} chars), truncating to {max_input_chars}")
            text = text[:max_input_chars] + "..."

        prompt = f"""
        Please summarize the following lecture transcription text concisely in Hebrew, focusing on the main topics or key points. Aim for 2-4 bullet points or a short paragraph ({max_length} words max).

        Transcription Text:
        ---
        {text}
        ---

        Summary:
        """

        try:
            logger.info(f"Requesting summary from OpenAI for text snippet starting with: '{text[:100]}...'")
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant skilled in summarizing lecture content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=350,
                n=1,
                stop=None,
            )

            # Safely access response content
            if response.choices and response.choices[0].message:
                 summary = response.choices[0].message.content
                 if summary:
                     summary = summary.strip().replace("Summary:", "").strip()
                     logger.info(f"Received summary: '{summary[:100]}...'")
                     return summary
                 else:
                      logger.warning("OpenAI response content was empty.")
                      return None
            else:
                 logger.warning("OpenAI response structure was unexpected or empty.")
                 return None

        except Exception as e:
            logger.error(f"Error calling OpenAI API for summarization: {e}", exc_info=True)
            return None

# Instantiate the service for use in other modules
summarization_service = SummarizationService()