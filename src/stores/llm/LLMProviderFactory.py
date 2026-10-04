from .LLMEnums import LLMEnums
from .providers import OpenAIProvider, CoHereProvider, GeminiProvider

class LLMProviderFactory:
    def __init__(self, config):
        self.config = config

    def create(self, provider: str):
        api_key = self.config.GENERATION_API_KEY
        api_url = self.config.GENERATION_API_URL
        max_chars = self.config.INPUT_DAFAULT_MAX_CHARACTERS
        max_tokens = self.config.GENERATION_MAX_TOKENS
        temperature = self.config.GENERATION_TEMPERATURE

        if provider == LLMEnums.OPENAI.value:
            return OpenAIProvider(
                api_key=api_key,
                api_url=api_url or None,
                default_input_max_characters=max_chars,
                default_generation_max_output_tokens=max_tokens,
                default_generation_temperature=temperature
            )

        if provider == LLMEnums.COHERE.value:
            return CoHereProvider(
                api_key=api_key,
                default_input_max_characters=max_chars,
                default_generation_max_output_tokens=max_tokens,
                default_generation_temperature=temperature
            )

        if provider == LLMEnums.GEMINI.value:
            return GeminiProvider(
                api_key=api_key,
                default_input_max_characters=max_chars,
                default_generation_max_output_tokens=max_tokens,
                default_generation_temperature=temperature
            )

        raise ValueError(f"Unsupported LLM provider: '{provider}'. "
                         f"Choose from: {[e.value for e in LLMEnums]}")
