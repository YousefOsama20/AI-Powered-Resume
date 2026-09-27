import spacy
import spacy.cli
from spacy.matcher import PhraseMatcher
import json
import os
import logging
from .BaseController import BaseController

logger = logging.getLogger("uvicorn.error")

class ExtractionController(BaseController):
    """
    Uses spaCy for NLP Tokenization & NER to extract technical skills 
    based on a predefined taxonomy.
    """
    _nlp = None

    def __init__(self):
        super().__init__()
        self.taxonomy_path = os.path.join(self.base_dir, "assets/taxonomy/skills-taxonomy.json")
        self._ensure_model_loaded()

    def _ensure_model_loaded(self):
        if ExtractionController._nlp is None:
            logger.info("[ExtractionController] Loading spaCy en_core_web_sm model...")
            try:
                ExtractionController._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.info("spaCy model not found. Downloading en_core_web_sm...")
                spacy.cli.download("en_core_web_sm")
                ExtractionController._nlp = spacy.load("en_core_web_sm")
            
        self._init_matcher()

    def _init_matcher(self):
        self.matcher = PhraseMatcher(ExtractionController._nlp.vocab, attr="LOWER")
        
        # Create default taxonomy if it doesn't exist
        if not os.path.exists(self.taxonomy_path):
            os.makedirs(os.path.dirname(self.taxonomy_path), exist_ok=True)
            default_taxonomy = [
                "python", "fastapi", "machine learning", "docker", "kubernetes", 
                "react", "typescript", "chromadb", "sql", "aws", "gcp", "azure",
                "nlp", "spacy", "deep learning", "node.js", "django", "flask",
                "c++", "java", "go", "ruby", "rust", "html", "css", "javascript"
            ]
            with open(self.taxonomy_path, "w") as f:
                json.dump(default_taxonomy, f, indent=4)
                
        with open(self.taxonomy_path, "r") as f:
            self.skills = json.load(f)
            
        patterns = [ExtractionController._nlp.make_doc(text) for text in self.skills]
        self.matcher.add("SKILLS", patterns)

    def extract_skills(self, text: str) -> list[str]:
        """Extracts skills from text based on the taxonomy."""
        if not text:
            return []
            
        doc = ExtractionController._nlp(text)
        matches = self.matcher(doc)
        
        extracted = set()
        for match_id, start, end in matches:
            span = doc[start:end]
            extracted.add(span.text.lower())
            
        return list(extracted)
