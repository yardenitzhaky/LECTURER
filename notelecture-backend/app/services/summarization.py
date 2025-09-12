# notelecture-backend/app/services/summarization.py
import logging
import httpx
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = "gpt-3.5-turbo"
        self.temperature = 0.6
        self.max_tokens = 350
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY":
            logger.warning("OpenAI API Key not configured. Summarization will be skipped.")
            self.api_key = None
        else:
            logger.info("OpenAI API client initialized successfully.") 

    async def summarize_text(self, text: str, slide_content: str = None, max_length: int = 75) -> str | None:
        """
        Generates a summary for the given text using OpenAI API.
        Returns the summary string or None if summarization fails or is skipped.
        """
        if not self.api_key:
            logger.info("Skipping summarization as OpenAI API key is not configured.")
            return None
        if not text or text.strip() == "":
            logger.info("Skipping summarization for empty text.")
            return None

        # Truncate text if it's extremely long
        max_input_chars = 8000
        if len(text) > max_input_chars:
            logger.warning(f"Input text too long ({len(text)} chars), truncating to {max_input_chars}")
            text = text[:max_input_chars] + "..."

        slide_section = ""
        if slide_content and slide_content.strip():
            slide_section = f"""
        Slide Content:
        ---
        {slide_content}
        ---
        """

        user_prompt = f"""
        You are analyzing lecture content. Your task is to summarize the transcription text in Hebrew, focusing specifically on how it relates to and explains the slide content shown.
        {slide_section}
        Transcription Text (what the lecturer said):
        ---
        {text}
        ---

        Instructions:
        - If slide content is available, prioritize summarizing the transcription based on how it explains, elaborates on, or relates to the slide content
        - Focus on the key explanations, examples, or details the lecturer provided about the slide topics
        - If no slide content is available, summarize the main topics and key points from the transcription
        - Provide a concise summary in Hebrew (2-4 bullet points or short paragraph, max {max_length} words)

        Summary:
        """

        return await self._generate_summary(text, user_prompt)

    async def summarize_with_custom_prompt(self, text: str, custom_prompt: str, slide_content: str = None) -> str | None:
        """
        Generates a summary for the given text using a custom user-provided prompt.
        Returns the summary string or None if summarization fails or is skipped.
        """
        if not self.api_key:
            logger.info("Skipping summarization as OpenAI API key is not configured.")
            return None
        if not text or text.strip() == "":
            logger.info("Skipping summarization for empty text.")
            return None
        if not custom_prompt or custom_prompt.strip() == "":
            logger.warning("Custom prompt is empty, falling back to default summarization")
            return await self.summarize_text(text, slide_content)

        # Truncate text if it's extremely long
        max_input_chars = 8000
        if len(text) > max_input_chars:
            logger.warning(f"Input text too long ({len(text)} chars), truncating to {max_input_chars}")
            text = text[:max_input_chars] + "..."

        slide_section = ""
        if slide_content and slide_content.strip():
            slide_section = f"""
        Slide Content:
        ---
        {slide_content}
        ---
        """

        # Sanitize and construct user prompt
        sanitized_prompt = custom_prompt.strip()[:1000]  # Limit prompt length
        user_prompt = f"""
        {sanitized_prompt}
        {slide_section}
        Transcription Text (what the lecturer said):
        ---
        {text}
        ---

        Instructions:
        - Focus on how the transcription text relates to and explains the slide content (if available)
        - Prioritize the lecturer's explanations, examples, or elaborations about the slide topics
        - Please provide your response in Hebrew.
        """

        return await self._generate_summary(text, user_prompt)

    async def _generate_summary(self, text: str, user_prompt: str) -> str | None:
        """
        Private method to generate summary using the provided prompt.
        """
        try:
            logger.info(f"Requesting summary from OpenAI API for text snippet starting with: '{text[:100]}...'")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant skilled in summarizing lecture content."},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if result and "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    summary = content.strip().replace("Summary:", "").strip()
                    logger.info(f"Received summary: '{summary[:100]}...'")
                    return summary
                else:
                    logger.warning("OpenAI API response content was empty.")
                    return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling OpenAI API: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error calling OpenAI API for summarization: {e}", exc_info=True)
            return None

# Instantiate the service for use in other modules
summarization_service = SummarizationService()