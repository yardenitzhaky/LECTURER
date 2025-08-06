# notelecture-backend/app/services/summarization.py
import logging
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self):
        self.llm: ChatOpenAI | None = None 
        if not settings.openai_api_key or settings.openai_api_key == "YOUR_OPENAI_API_KEY":
            logger.warning("OpenAI API Key not configured. Summarization will be skipped.")
        else:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    openai_api_key=settings.openai_api_key,
                    temperature=0.6,
                    max_tokens=350,
                    request_timeout=60
                )
                logger.info("LangChain ChatOpenAI initialized successfully.")

            except Exception as e:
                logger.error(f"Failed to initialize LangChain ChatOpenAI: {e}", exc_info=True)
                self.llm = None 

    async def summarize_text(self, text: str, max_length: int = 75) -> str | None:
        """
        Generates a summary for the given text using LangChain ChatOpenAI.
        Returns the summary string or None if summarization fails or is skipped.
        """
        if not self.llm:
            logger.info("Skipping summarization as LangChain ChatOpenAI is not initialized.")
            return None
        if not text or text.strip() == "":
            logger.info("Skipping summarization for empty text.")
            return None

        # Truncate text if it's extremely long
        max_input_chars = 8000
        if len(text) > max_input_chars:
            logger.warning(f"Input text too long ({len(text)} chars), truncating to {max_input_chars}")
            text = text[:max_input_chars] + "..."

        user_prompt = f"""
        Please summarize the following lecture transcription text concisely in Hebrew, focusing on the main topics or key points. Aim for 2-4 bullet points or a short paragraph ({max_length} words max).

        Transcription Text:
        ---
        {text}
        ---

        Summary:
        """

        return await self._generate_summary(text, user_prompt)

    async def summarize_with_custom_prompt(self, text: str, custom_prompt: str) -> str | None:
        """
        Generates a summary for the given text using a custom user-provided prompt.
        Returns the summary string or None if summarization fails or is skipped.
        """
        if not self.llm:
            logger.info("Skipping summarization as LangChain ChatOpenAI is not initialized.")
            return None
        if not text or text.strip() == "":
            logger.info("Skipping summarization for empty text.")
            return None
        if not custom_prompt or custom_prompt.strip() == "":
            logger.warning("Custom prompt is empty, falling back to default summarization")
            return await self.summarize_text(text)

        # Truncate text if it's extremely long
        max_input_chars = 8000
        if len(text) > max_input_chars:
            logger.warning(f"Input text too long ({len(text)} chars), truncating to {max_input_chars}")
            text = text[:max_input_chars] + "..."

        # Sanitize and construct user prompt
        sanitized_prompt = custom_prompt.strip()[:1000]  # Limit prompt length
        user_prompt = f"""
        {sanitized_prompt}

        Transcription Text:
        ---
        {text}
        ---

        Please provide your response in Hebrew.
        """

        return await self._generate_summary(text, user_prompt)

    async def _generate_summary(self, text: str, user_prompt: str) -> str | None:
        """
        Private method to generate summary using the provided prompt.
        """
        try:
            logger.info(f"Requesting summary from LangChain ChatOpenAI for text snippet starting with: '{text[:100]}...'")
            
            messages = [
                SystemMessage(content="You are a helpful assistant skilled in summarizing lecture content."),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)

            if response and response.content:
                summary = response.content.strip().replace("Summary:", "").strip()
                logger.info(f"Received summary: '{summary[:100]}...'")
                return summary
            else:
                logger.warning("LangChain response content was empty.")
                return None

        except Exception as e:
            logger.error(f"Error calling LangChain ChatOpenAI for summarization: {e}", exc_info=True)
            return None

# Instantiate the service for use in other modules
summarization_service = SummarizationService()