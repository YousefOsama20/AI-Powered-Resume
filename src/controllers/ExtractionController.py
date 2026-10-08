import spacy
import spacy.cli
from spacy.matcher import PhraseMatcher
import json
import os
import re
import logging
from .BaseController import BaseController
from models.enums import DefaultTaxonomy

logger = logging.getLogger("uvicorn.error")

# Markers that introduce the "nice to have / elective" section of a JD.
# Used by the heuristic fallback when the LLM is unavailable or returns empty.
ELECTIVE_SECTION_PATTERNS = [
    r"nice\s*to\s*have",
    r"nice-to-have",
    r"preferred(?:\s+skills)?",
    r"bonus(?:\s+points)?",
    r"\ba\s+plus\b",
    r"desirable",
    r"beneficial",
    r"\boptional\b",
    r"would\s+be\s+a\s+plus",
    r"is\s+a\s+plus",
    r"is\s+preferred",
]

class ExtractionController(BaseController):
    """
    Uses spaCy for NLP Tokenization & NER to extract technical skills 
    based on a predefined taxonomy.
    
    Supports a categorized taxonomy (dict of track -> skills list) 
    and a flat taxonomy (plain list of skills) for backward compatibility.
    
    - During indexing: uses the FULL taxonomy to capture all possible skills.
    - During JD matching: caller can pass filter_skills to narrow extraction.
    """
    _nlp = None

    def __init__(self):
        # Type: Sub-function
        super().__init__()
        self.taxonomy_path = os.path.join(self.base_dir, "assets/taxonomy/skills-taxonomy.json")
        self._ensure_model_loaded()

    def _ensure_model_loaded(self):
        # Lazy-load spaCy NLP model. | Internal
        # Type: Sub-function
        if ExtractionController._nlp is None:
            logger.info("[ExtractionController] Loading spaCy en_core_web_sm model...")
            try:
                ExtractionController._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.info("spaCy model not found. Downloading en_core_web_sm...")
                spacy.cli.download("en_core_web_sm")
                ExtractionController._nlp = spacy.load("en_core_web_sm")
            
        self._init_matcher()

    def _load_taxonomy(self) -> dict:
        # Load skills taxonomy YAML from assets. | Internal
        # Type: Sub-function
        """
        Loads the taxonomy file.
        Returns a dict of {track_name: [skills]} if categorized,
        or {"_flat": [skills]} if the file is a flat list.
        """
        if not os.path.exists(self.taxonomy_path):
            os.makedirs(os.path.dirname(self.taxonomy_path), exist_ok=True)

            default_taxonomy = DefaultTaxonomy()

            with open(self.taxonomy_path, "w") as f:
                json.dump(default_taxonomy, f, indent=4)

        with open(self.taxonomy_path, "r") as f:
            data = json.load(f)

        # Support both flat list (legacy) and categorized dict (new)
        if isinstance(data, list):
            return {"_flat": data}
        return data

    def _flatten_taxonomy(self, taxonomy: dict) -> list:
        # Flatten nested taxonomy dict into a flat skills list. | Internal
        # Type: Sub-function
        """Flattens a categorized taxonomy dict into a deduplicated list of all skills."""
        all_skills = []
        seen = set()
        for track_skills in taxonomy.values():
            for skill in track_skills:
                skill_lower = skill.lower()
                if skill_lower not in seen:
                    seen.add(skill_lower)
                    all_skills.append(skill_lower)
        return all_skills

    def _build_matcher(self, skills: list) -> PhraseMatcher:
        # Build a spaCy PhraseMatcher from a list of skill strings. | Internal
        # Type: Sub-function
        """Builds a PhraseMatcher from a list of skill strings."""
        matcher = PhraseMatcher(ExtractionController._nlp.vocab, attr="LOWER")
        patterns = [ExtractionController._nlp.make_doc(text) for text in skills]
        if patterns:
            matcher.add("SKILLS", patterns)
        return matcher

    def _init_matcher(self):
        # Initialize the spaCy matcher with all taxonomy skills. | Internal
        # Type: Sub-function
        """Initializes the full taxonomy and the default (full) matcher."""
        self.taxonomy = self._load_taxonomy()
        self.skills = self._flatten_taxonomy(self.taxonomy)
        self.matcher = self._build_matcher(self.skills)
        logger.info(
            f"[ExtractionController] Loaded {len(self.skills)} skills "
            f"across {len(self.taxonomy)} tracks."
        )

    def get_all_skills(self) -> list:
        # Return all skills from the taxonomy. | Internal
        # Type: Main function
        """Returns the full flat list of all skills from all tracks."""
        return list(self.skills)

    def get_skills_by_track(self, track_name: str) -> list:
        # Return skills for a specific track (e.g. "Python"). | Internal
        # Type: Main function
        """Returns skills for a specific career track."""
        return self.taxonomy.get(track_name, [])

    def get_track_names(self) -> list:
        # Return all track names in the taxonomy. | Internal
        # Type: Main function
        """Returns all available track names."""
        return [k for k in self.taxonomy.keys() if k != "_flat"]

    def extract_skills(self, text: str, filter_skills: list = None) -> list:
        # Extract matching skills from text using spaCy NLP. | Both (CV and JD skill extraction)
        # Type: Main function
        """
        Extracts skills from text based on the taxonomy.
        
        Args:
            text: The text to extract skills from.
            filter_skills: Optional list of skills to restrict extraction to.
                          If None, uses the full taxonomy (for indexing).
                          If provided, only these skills are matched (for JD filtering).
        
        Returns:
            List of extracted skill strings (lowercased).
        """
        if not text:
            return []

        doc = ExtractionController._nlp(text)

        if filter_skills is not None:
            # Build a temporary matcher for just the specified skills
            temp_matcher = self._build_matcher(filter_skills)
            matches = temp_matcher(doc)
        else:
            # Use the full taxonomy matcher
            matches = self.matcher(doc)
        
        extracted = set()
        for match_id, start, end in matches:
            span = doc[start:end]
            try:
                from .SkillNormalizer import normalize_skill as _canon_one
                v = _canon_one(span.text)
            except Exception:
                v = span.text.lower()
            if v:
                extracted.add(v)
            
        return list(extracted)

    @staticmethod
    def split_jd_sections(job_description: str) -> tuple:
        """Split JD text into (essential_part, elective_part) using elective markers.

        Returns the full text as essential_part and "" as elective_part when no
        marker is found, so callers can safely fall back to all-essential.
        """
        if not job_description:
            return "", ""
        combined = "|".join(f"(?:{p})" for p in ELECTIVE_SECTION_PATTERNS)
        match = re.search(combined, job_description, flags=re.IGNORECASE)
        if not match:
            return job_description, ""
        return job_description[:match.start()], job_description[match.start():]

    def extract_classified_skills(self, job_description: str) -> dict:
        """Heuristic essential/elective split without needing an LLM.

        Extracts taxonomy skills from the "required" part and the
        "nice to have" part separately. A skill appearing in both stays
        essential-only. Returns {"essential": [...], "elective": [...]}.
        """
        if not job_description:
            return {"essential": [], "elective": []}
        essential_part, elective_part = self.split_jd_sections(job_description)
        essential = set(self.extract_skills(essential_part)) if essential_part else set()
        elective = set(self.extract_skills(elective_part)) if elective_part else set()
        # A skill in both sections is treated as required.
        elective = {s for s in elective if s not in essential}
        # If the JD has no detectable elective section, everything is essential
        # (previous behaviour) — but at least the split was attempted.
        if not elective_part:
            return {"essential": sorted(essential), "elective": []}
        return {"essential": sorted(essential), "elective": sorted(elective)}
