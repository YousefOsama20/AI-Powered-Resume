"""
LLMProvider
───────────
Backend-agnostic LLM client.
Uses LLMProviderFactory to create the correct provider based on settings.
Supports OpenAI, Cohere, Gemini, and any provider registered in the factory.
"""

import logging
from .LLMProviderFactory import LLMProviderFactory

logger = logging.getLogger("uvicorn.error")


class LLMProvider:
    """
    Wraps the LLMProviderFactory to provide a simple generate() interface.
    Automatically selects the correct backend (OpenAI, Cohere, Gemini)
    based on GENERATION_BACKEND in settings.
    """

    def __init__(self, api_key: str, api_url: str, model_id: str,
                 max_tokens: int = 500, temperature: float = 0.1,
                 backend: str = "OPENAI"):
        # Type: Sub-function
        """Initializes the LLM client via the factory based on the backend setting."""
        from helpers.config import get_settings
        settings = get_settings()

        factory = LLMProviderFactory(settings)
        self.provider = factory.create(provider=settings.GENERATION_BACKEND)
        self.provider.set_generation_model(model_id=model_id)

        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        logger.info(f"[LLMProvider] Initialized with model: {model_id}, backend: {settings.GENERATION_BACKEND}")

    def generate(self, system_prompt: str, user_prompt: str,
                 max_tokens: int = None, temperature: float = None) -> str:
        # Type: Main function
        """
        Sends a prompt to the LLM and returns the text response.
        Delegates to the underlying provider's generate_text method.
        """
        try:
            # Build chat history with system prompt
            chat_history = [
                self.provider.construct_prompt(prompt=system_prompt, role="system")
            ]

            result = self.provider.generate_text(
                prompt=user_prompt,
                chat_history=chat_history,
                max_output_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature
            )

            if result:
                logger.info(f"[LLMProvider] Generated response ({len(result)} chars)")
            else:
                logger.warning("[LLMProvider] Provider returned empty response")
                result = ""

            return result
        except Exception as e:
            logger.error(f"[LLMProvider] Error generating response: {e}")
            return ""

