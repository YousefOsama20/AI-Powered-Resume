from ..LLMInterface import LLMInterface
from ..LLMEnums import GeminiEnums
from google import genai
from google.genai import types
import logging


class GeminiProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1
    ):

        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = genai.Client(
            api_key=self.api_key
        )

        self.enums = GeminiEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = None,
        temperature: float = None
    ):

        if not self.client:
            self.logger.error("Gemini client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Gemini was not set")
            return None

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_max_output_tokens
        )

        temperature = (
            temperature
            if temperature is not None
            else self.default_generation_temperature
        )

        # -----------------------------------------
        # 1. Extract system prompt
        # -----------------------------------------

        system_instruction = None

        # -----------------------------------------
        # 2. Build Gemini conversation history
        # -----------------------------------------

        contents = []

        for message in chat_history:

            role = message["role"]
            text = message["text"]

            # Gemini does NOT accept "system"
            if role == GeminiEnums.SYSTEM.value:
                system_instruction = text
                continue

            # Convert assistant -> model
            if role == GeminiEnums.ASSISTANT.value:
                role = GeminiEnums.MODEL.value

            # Gemini supports user/model
            if role not in [
                GeminiEnums.USER.value,
                GeminiEnums.MODEL.value
            ]:
                self.logger.warning(
                    f"Unsupported Gemini role: {role}"
                )
                continue

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=text
                        )
                    ]
                )
            )

        # -----------------------------------------
        # 3. Add current user prompt
        # -----------------------------------------

        contents.append(
            types.Content(
                role=GeminiEnums.USER.value,
                parts=[
                    types.Part.from_text(
                        text=self.process_text(prompt)
                    )
                ]
            )
        )

        # -----------------------------------------
        # 4. Generate response
        # -----------------------------------------

        config = types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            system_instruction=system_instruction
        )

        response = self.client.models.generate_content(
            model=self.generation_model_id,
            contents=contents,
            config=config
        )

        if not response or not response.text:
            self.logger.error(
                "Error while generating text with Gemini"
            )
            return None

        return response.text

    def embed_text(
        self,
        text: str,
        document_type: str = None
    ):

        if not self.client:
            self.logger.error("Gemini client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error(
                "Embedding model for Gemini was not set"
            )
            return None

        response = self.client.models.embed_content(
            model=self.embedding_model_id,
            contents=self.process_text(text),
        )

        if (
            not response
            or not response.embeddings
            or len(response.embeddings) == 0
        ):
            self.logger.error(
                "Error while embedding text with Gemini"
            )
            return None

        return response.embeddings[0].values

    def construct_prompt(
        self,
        prompt: str,
        role: str
    ):

        return {
            "role": role,
            "text": self.process_text(prompt)
        }
        