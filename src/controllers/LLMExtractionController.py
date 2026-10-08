"""
LLMExtractionController
───────────────────────
Uses an LLM (via OpenAI-compatible API) to extract skills from
Job Descriptions and CVs.

For JDs: Returns classified skills {"essential": [...], "elective": [...]}
For CVs: Returns a flat list of skills [...]

Prompts are loaded from the templates system (locales/en/skill_extraction.py)
following the same pattern as MiniRAG's TemplateParser.
"""

import json
import re
import logging
from typing import List, Dict, Optional, Union

from .BaseController import BaseController
from stores.llm import LLMProvider
from stores.llm.templates.template_parser import TemplateParser

logger = logging.getLogger("uvicorn.error")


class LLMExtractionController(BaseController):
    """
    Extracts skills from job descriptions and CVs using an LLM.
    JD extraction returns classified skills (essential/elective).
    CV extraction returns a flat skill list.
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
        # Lazy-load the LLM client (Groq/OpenAI). | Internal
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

    def _normalize_skill_list(self, raw_list: list) -> List[str]:
        # Clean and deduplicate a raw skill list. | Internal helper
        # Type: Sub-function
        """Normalizes a list of skills via SkillNormalizer (canonical aliases,
        plural handling, dedupe). Normalization is idempotent."""
        try:
            from .SkillNormalizer import normalize_skill_list as _canon
            cleaned = [s for s in (raw_list or []) if isinstance(s, str)]
            return _canon(cleaned)
        except Exception:
            # Fallback to legacy behavior if normalizer import fails
            seen = set()
            result = []
            for s in raw_list:
                if isinstance(s, str):
                    normalized = s.strip().lower()
                    if normalized and normalized not in seen:
                        seen.add(normalized)
                        result.append(normalized)
            return result

    def _parse_skills_response(self, response: str) -> List[str]:
        # Parse LLM text response into a list of skills. | Internal helper
        # Type: Sub-function
        """
        Parses the LLM response into a clean list of skills (for CVs).
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
                return self._normalize_skill_list(skills)
        except json.JSONDecodeError:
            logger.warning(f"[LLMExtractionController] Failed to parse JSON from LLM response: {cleaned[:200]}")

        # Fallback: try to extract skills from comma-separated or newline-separated text
        fallback_skills = []
        for line in cleaned.replace(',', '\n').split('\n'):
            skill = line.strip().strip('-').strip('•').strip('"').strip("'").strip().lower()
            if skill and len(skill) < 50:  # sanity check
                fallback_skills.append(skill)

        return list(set(fallback_skills))

    def _parse_classified_skills_response(self, response: str) -> Dict[str, List[str]]:
        # Parse LLM response into essential vs elective skill categories. | Internal helper
        # Type: Sub-function
        """
        Parses the LLM response into classified skills (for JDs).
        Expected format: {"essential": [...], "elective": [...]}
        Falls back to putting all skills in "essential" if parsing fails.
        """
        if not response:
            return {"essential": [], "elective": []}

        # Strip markdown code blocks
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                essential = self._normalize_skill_list(parsed.get("essential", []))
                elective = self._normalize_skill_list(parsed.get("elective", []))
                logger.info(f"[LLMExtractionController] Classified: {len(essential)} essential, {len(elective)} elective")
                return {"essential": essential, "elective": elective}
            elif isinstance(parsed, list):
                # LLM returned a flat list instead of classified — treat all as essential
                logger.warning("[LLMExtractionController] LLM returned flat list instead of classified. Treating all as essential.")
                return {"essential": self._normalize_skill_list(parsed), "elective": []}
        except json.JSONDecodeError:
            logger.warning(f"[LLMExtractionController] Failed to parse classified JSON: {cleaned[:200]}")

        # Last resort fallback: try to extract as flat list and put all in essential
        fallback = self._parse_skills_response(response)
        return {"essential": fallback, "elective": []}

    def extract_skills_from_jd(self, job_description: str) -> Dict[str, List[str]]:
        # Use LLM to classify JD skills into essential and elective. | Company (JD processing)
        # Type: Main function
        """
        Extracts and classifies skills from a job description using the LLM.

        Args:
            job_description: The full job description text.

        Returns:
            Dictionary with "essential" and "elective" skill lists.
            Returns {"essential": [], "elective": []} if LLM is not available.
        """
        if not job_description or not job_description.strip():
            return {"essential": [], "elective": []}

        if self._llm_provider is None:
            logger.warning("[LLMExtractionController] LLM not available. Returning empty skills.")
            return {"essential": [], "elective": []}

        # Load prompts from template system
        system_prompt = self.template_parser.get("skill_extraction", "system_prompt")
        user_prompt = self.template_parser.get(
            "skill_extraction", "user_prompt",
            vars={"job_description": job_description}
        )

        if not system_prompt or not user_prompt:
            logger.error("[LLMExtractionController] Failed to load prompt templates.")
            return {"essential": [], "elective": []}

        response = self._llm_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        classified = self._parse_classified_skills_response(response)
        total = len(classified["essential"]) + len(classified["elective"])
        logger.info(f"[LLMExtractionController] Extracted {total} skills from JD via LLM ({len(classified['essential'])} essential, {len(classified['elective'])} elective)")
        return classified

    def extract_skills_from_cv(self, resume_text: str) -> List[str]:
        # Use LLM to extract skills from a candidate CV. | Customer (CV processing)
        # Type: Main function
        """
        Extracts all skills from a CV/resume using the LLM.
        Returns a flat list (no classification needed for CVs).

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
        # Check if the LLM backend is properly configured. | Internal
        # Type: Main function
        """Returns True if the LLM provider is configured and ready."""
        return self._llm_provider is not None
