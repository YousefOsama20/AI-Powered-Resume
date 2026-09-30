import spacy
import spacy.cli
from spacy.matcher import PhraseMatcher
import json
import os
import logging
from .BaseController import BaseController
from models.enums import DefaultTaxonomy

logger = logging.getLogger("uvicorn.error")

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
        # Type: Sub-function
        """Builds a PhraseMatcher from a list of skill strings."""
        matcher = PhraseMatcher(ExtractionController._nlp.vocab, attr="LOWER")
        patterns = [ExtractionController._nlp.make_doc(text) for text in skills]
        if patterns:
            matcher.add("SKILLS", patterns)
        return matcher

    def _init_matcher(self):
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
        # Type: Main function
        """Returns the full flat list of all skills from all tracks."""
        return list(self.skills)

    def get_skills_by_track(self, track_name: str) -> list:
        # Type: Main function
        """Returns skills for a specific career track."""
        return self.taxonomy.get(track_name, [])

    def get_track_names(self) -> list:
        # Type: Main function
        """Returns all available track names."""
        return [k for k in self.taxonomy.keys() if k != "_flat"]

    def extract_skills(self, text: str, filter_skills: list = None) -> list:
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
            extracted.add(span.text.lower())
            
        return list(extracted)
