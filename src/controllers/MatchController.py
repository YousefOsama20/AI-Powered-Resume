"""
MatchController
───────────────
Implements the Hybrid Ranking Engine:
Semantic Score (Cosine) + Keyword Score (Jaccard) + Experience Score.

Uses LLM-based extraction for JD skills (catches ALL skills),
and taxonomy-based extraction for CV skills (stored during indexing).
"""

import logging
from .VectorDBController import VectorDBController
from .EmbeddingController import EmbeddingController
from .ExtractionController import ExtractionController
from .ExperienceController import ExperienceController
from .LLMExtractionController import LLMExtractionController
from typing import List, Dict, Any

logger = logging.getLogger("uvicorn.error")


class MatchController:
    """
    Implements the Hybrid Ranking Engine: 
    Calculates Semantic Score (Cosine), Keyword Score (Jaccard),
    and Experience Score with a 35% Semantic / 35% Keyword / 30% Experience weighting.
    """
    def __init__(self):
        # Type: Sub-function
        """Initializes MatchController and sub-controllers."""
        self.vector_db = VectorDBController()
        self.embedding = EmbeddingController()
        self.extraction = ExtractionController()
        self.experience = ExperienceController()
        self.llm_extraction = LLMExtractionController()
        
    def match_candidates(self, job_description: str, project_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Type: Main function
        """
        Matches a job description against candidates and ranks them.
        Uses LLM to extract JD skills if available, otherwise falls back to taxonomy.
        """
        # 1. Extract JD skills — prefer LLM (catches ALL skills), fallback to taxonomy
        if self.llm_extraction.is_available:
            jd_skills = set(self.llm_extraction.extract_skills_from_jd(job_description))
            logger.info(f"[MatchController] LLM extracted {len(jd_skills)} JD skills: {jd_skills}")
        else:
            jd_skills = set(self.extraction.extract_skills(job_description))
            logger.info(f"[MatchController] Taxonomy extracted {len(jd_skills)} JD skills (LLM unavailable)")

        jd_embedding = self.embedding.embed_text(job_description)
        required_exp = self.experience.extract_required_experience(job_description)
        
        if not jd_embedding:
            return []
            
        # 2. Retrieve candidates semantically (broad search)
        results = self.vector_db.search(
            query_embedding=jd_embedding,
            project_id=project_id,
            n_results=100  # fetch broad pool to rerank
        )
        
        if not results:
            return []
            
        # Group by candidate (file_id)
        candidates = {}
        for res in results:
            file_id = res["metadata"].get("file_id")
            if not file_id:
                continue
                
            if file_id not in candidates:
                candidates[file_id] = {
                    "semantic_scores": [],
                    "skills": set(),
                    "experience_chunks_text": [],
                    "experience_years_fallback": 0.0
                }
            
            # Keep track of chunk scores
            candidates[file_id]["semantic_scores"].append(res["score"])
            
            # Aggregate skills extracted from candidate chunks
            chunk_skills = res["metadata"].get("skills", "")
            if chunk_skills:
                for skill in chunk_skills.split(","):
                    candidates[file_id]["skills"].add(skill.strip().lower())

            # Collect Experience-section chunk text for re-extraction
            if res["metadata"].get("section") == "Experience":
                # Collect the full chunk text for combined date parsing
                chunk_text = res.get("document", "")
                if chunk_text:
                    candidates[file_id]["experience_chunks_text"].append(chunk_text)
                # Also keep pre-computed value as fallback
                chunk_exp = res["metadata"].get("experience_years", 0)
                if isinstance(chunk_exp, (int, float)):
                    candidates[file_id]["experience_years_fallback"] = max(
                        candidates[file_id]["experience_years_fallback"],
                        float(chunk_exp)
                    )
                    
        # 3. Score and rank candidates
        ranked_candidates = []
        for file_id, data in candidates.items():
            # Average semantic score of the chunks for this candidate
            avg_semantic = sum(data["semantic_scores"]) / len(data["semantic_scores"])
            
            # Keyword score (Jaccard Index)
            candidate_skills = data["skills"]
            if not jd_skills and not candidate_skills:
                jaccard = 0.0
            elif not jd_skills:
                jaccard = 1.0 # JD has no specific requirements extracted
            else:
                intersection = candidate_skills.intersection(jd_skills)
                union = candidate_skills.union(jd_skills)
                jaccard = len(intersection) / len(union) if union else 0.0

            # Experience score
            combined_exp_text = "\n\n".join(data["experience_chunks_text"])
            candidate_exp = self.experience.extract_candidate_experience(combined_exp_text)
            
            if candidate_exp == 0.0:
                candidate_exp = data["experience_years_fallback"]
                
            exp_score = self.experience.calculate_experience_score(required_exp, candidate_exp)

            # Experience gap (how many years short)
            if required_exp and candidate_exp < required_exp:
                experience_gap = round(required_exp - candidate_exp, 1)
            else:
                experience_gap = 0
                
            # Weighted Hybrid Score: 35% Semantic / 35% Keyword / 30% Experience
            hybrid_score = (avg_semantic * 0.35) + (jaccard * 0.35) + (exp_score * 0.30)
            
            missing_skills = list(jd_skills - candidate_skills)
            matched_skills = list(jd_skills.intersection(candidate_skills))
            
            ranked_candidates.append({
                "candidate_id": file_id,
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(avg_semantic * 100, 2),
                "keyword_score": round(jaccard * 100, 2),
                "experience_score": round(exp_score * 100, 2),
                "required_experience": required_exp,
                "candidate_experience": candidate_exp,
                "experience_gap": experience_gap,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "extracted_skills": list(candidate_skills)
            })
            
        # Sort by hybrid match_score descending
        ranked_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked_candidates[:top_k], list(jd_skills)
