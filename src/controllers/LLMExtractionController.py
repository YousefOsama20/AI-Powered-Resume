"""
LLMExtractionController
───────────────────────
Uses an LLM (via OpenAI-compatible API) to extract ALL skills from a
Job Description — including skills not in the predefined taxonomy.

Prompts are loaded from the templates system (locales/en/skill_extraction.py)
following the same pattern as MiniRAG's TemplateParser.
"""

import json
import re
import logging
from typing import List, Optional

from .BaseController import BaseController
from stores.llm import LLMProvider
from stores.llm.templates.template_parser import TemplateParser

logger = logging.getLogger("uvicorn.error")


class LLMExtractionController(BaseController):
    """
    Extracts skills from job descriptions using an LLM.
    Falls back to taxonomy-based extraction if LLM is unavailable.
    """

    _llm_provider: Optional[LLMProvider] = None

    def __init__(self):
        # Type: Sub-function
        """Initializes the LLM extraction controller."""
        super().__init__()
        self.template_parser = TemplateParser(
            language=self.app_settings.PRIMARY_LANG,
            default_language=self.app_settings.DEFAULT_LANG
        )
        self._ensure_llm_loaded()

    def _ensure_llm_loaded(self):
        # Type: Sub-function
        """Lazily initializes the LLM provider from app settings."""
        if LLMExtractionController._llm_provider is None:
            settings = self.app_settings

            # Check if LLM is configured
            if not settings.GENERATION_MODEL_ID:
                logger.warning("[LLMExtractionController] No GENERATION_MODEL_ID configured. LLM extraction disabled.")
                return

            try:
                LLMExtractionController._llm_provider = LLMProvider(
                    api_key=settings.GENERATION_API_KEY,
                    api_url=settings.GENERATION_API_URL,
                    model_id=settings.GENERATION_MODEL_ID,
                    max_tokens=settings.GENERATION_MAX_TOKENS,
                    temperature=settings.GENERATION_TEMPERATURE
                )
                logger.info("[LLMExtractionController] LLM provider initialized successfully.")
            except Exception as e:
                logger.error(f"[LLMExtractionController] Failed to initialize LLM: {e}")

    def _parse_skills_response(self, response: str) -> List[str]:
        # Type: Sub-function
        """
        Parses the LLM response into a clean list of skills.
        Handles cases where LLM wraps JSON in markdown code blocks.
        """
        if not response:
            return []

        # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()

        try:
            skills = json.loads(cleaned)
            if isinstance(skills, list):
                # Normalize: lowercase, strip, deduplicate, remove empties
                seen = set()
                result = []
                for s in skills:
                    if isinstance(s, str):
                        normalized = s.strip().lower()
                        if normalized and normalized not in seen:
                            seen.add(normalized)
                            result.append(normalized)
                return result
        except json.JSONDecodeError:
            logger.warning(f"[LLMExtractionController] Failed to parse JSON from LLM response: {cleaned[:200]}")

        # Fallback: try to extract skills from comma-separated or newline-separated text
        fallback_skills = []
        for line in cleaned.replace(',', '\n').split('\n'):
            skill = line.strip().strip('-').strip('•').strip('"').strip("'").strip().lower()
            if skill and len(skill) < 50:  # sanity check
                fallback_skills.append(skill)

        return list(set(fallback_skills))

    def extract_skills_from_jd(self, job_description: str) -> List[str]:
        # Type: Main function
        """
        Extracts all skills from a job description using the LLM.
        Prompts are loaded from templates/locales/{lang}/skill_extraction.py.

        Args:
            job_description: The full job description text.

        Returns:
            List of extracted skill strings (lowercased).
            Returns empty list if LLM is not available.
        """
        if not job_description or not job_description.strip():
            return []

        if self._llm_provider is None:
            logger.warning("[LLMExtractionController] LLM not available. Returning empty skills.")
            return []

        # Load prompts from template system
        system_prompt = self.template_parser.get("skill_extraction", "system_prompt")
        user_prompt = self.template_parser.get(
            "skill_extraction", "user_prompt",
            vars={"job_description": job_description}
        )

        if not system_prompt or not user_prompt:
            logger.error("[LLMExtractionController] Failed to load prompt templates.")
            return []

        response = self._llm_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        skills = self._parse_skills_response(response)
        logger.info(f"[LLMExtractionController] Extracted {len(skills)} skills from JD via LLM")
        return skills

    def extract_skills_from_cv(self, resume_text: str) -> List[str]:
        # Type: Main function
        """
        Extracts all skills from a CV/resume using the LLM.
        Prompts are loaded from templates/locales/{lang}/skill_extraction.py.

        Args:
            resume_text: The full resume text (all sections combined).

        Returns:
            List of extracted skill strings (lowercased).
            Returns empty list if LLM is not available.
        """
        if not resume_text or not resume_text.strip():
            return []

        if self._llm_provider is None:
            logger.warning("[LLMExtractionController] LLM not available for CV extraction.")
            return []

        # Load CV-specific prompts from template system
        system_prompt = self.template_parser.get("skill_extraction", "cv_system_prompt")
        user_prompt = self.template_parser.get(
            "skill_extraction", "cv_user_prompt",
            vars={"resume_text": resume_text}
        )

        if not system_prompt or not user_prompt:
            logger.error("[LLMExtractionController] Failed to load CV prompt templates.")
            return []

        response = self._llm_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        skills = self._parse_skills_response(response)
        logger.info(f"[LLMExtractionController] Extracted {len(skills)} skills from CV via LLM")
        return skills

    @property
    def is_available(self) -> bool:
        # Type: Main function
        """Returns True if the LLM provider is configured and ready."""
        return self._llm_provider is not None
