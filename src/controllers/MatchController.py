"""
MatchController
───────────────
Implements the Hybrid Ranking Engine:
Semantic Score (Cosine) + Keyword Score (Essential/Elective) + Experience Score.

Skills are now classified into Essential (75% of keyword score) and
Elective (25% of keyword score) for more accurate matching.
"""

import logging
from .VectorDBController import VectorDBController
from .EmbeddingController import EmbeddingController
from .ExtractionController import ExtractionController
from .ExperienceController import ExperienceController
from .LLMExtractionController import LLMExtractionController
from .JDController import JDController
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("uvicorn.error")


class MatchController:
    """
    Implements the Hybrid Ranking Engine: 
    Calculates Semantic Score (Cosine), Keyword Score (Essential 75% + Elective 25%),
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
        self.jd_controller = JDController()
        
    def match_candidates(self, customer_id: str = None, job_description: str = None, 
                               jd_name: str = None, top_k: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        # Type: Main function
        """
        Matches a job description against candidates and ranks them.
        Skills are classified into essential and elective for weighted scoring.
        Searches the Global Candidate Pool unless a specific customer_id is provided.
        """
        essential_skills = set()
        elective_skills = set()
        required_exp = 0.0
        jd_embedding = None

        if jd_name:
            # Load precomputed data
            stored_jd = self.jd_controller.get_jd(jd_name)
            if stored_jd:
                skills_data = stored_jd.get("skills", {})
                essential_skills = set(skills_data.get("essential", []))
                elective_skills = set(skills_data.get("elective", []))
                required_exp = stored_jd.get("required_experience", 0.0)
                jd_embedding = stored_jd.get("embedding")
                logger.info(f"[MatchController] Loaded JD '{jd_name}' with {len(essential_skills)} essential + {len(elective_skills)} elective skills")
            else:
                logger.warning(f"[MatchController] JD '{jd_name}' not found, falling back to on-the-fly extraction")

        if jd_embedding is None or len(jd_embedding) == 0:
            # Fallback to on-the-fly extraction if not stored or no jd_name
            if not job_description:
                return [], {}
            
            # Extract JD skills — prefer LLM (classified), fallback to taxonomy (all essential)
            if self.llm_extraction.is_available:
                classified = self.llm_extraction.extract_skills_from_jd(job_description)
                essential_skills = set(classified.get("essential", []))
                elective_skills = set(classified.get("elective", []))
                logger.info(f"[MatchController] LLM extracted {len(essential_skills)} essential + {len(elective_skills)} elective skills on the fly")
            else:
                essential_skills = set(self.extraction.extract_skills(job_description))
                elective_skills = set()
                logger.info(f"[MatchController] Taxonomy extracted {len(essential_skills)} skills as essential (LLM unavailable)")

            jd_embedding = self.embedding.embed_text(job_description)
            required_exp = self.experience.extract_required_experience(job_description)
        
        if jd_embedding is None or len(jd_embedding) == 0:
            return [], {}
            
        # 2. Retrieve candidates semantically (broad search)
        results = self.vector_db.search(
            query_embedding=jd_embedding,
            customer_id=customer_id,
            n_results=100  # fetch broad pool to rerank
        )
        
        if not results:
            return [], {}
            
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
                chunk_text = res.get("document", "")
                if chunk_text:
                    candidates[file_id]["experience_chunks_text"].append(chunk_text)
                chunk_exp = res["metadata"].get("experience_years", 0)
                if isinstance(chunk_exp, (int, float)):
                    candidates[file_id]["experience_years_fallback"] = max(
                        candidates[file_id]["experience_years_fallback"],
                        float(chunk_exp)
                    )
                    
        # 3. Score and rank candidates
        all_jd_skills = essential_skills | elective_skills
        ranked_candidates = []

        for file_id, data in candidates.items():
            # Average semantic score of the chunks for this candidate
            avg_semantic = sum(data["semantic_scores"]) / len(data["semantic_scores"])
            
            candidate_skills = data["skills"]

            # ── Keyword Score with Essential/Elective Weighting ──
            # Essential Score (75% weight): what % of essential skills does candidate have?
            if essential_skills:
                essential_matched = candidate_skills.intersection(essential_skills)
                essential_score = len(essential_matched) / len(essential_skills)
            else:
                essential_matched = set()
                essential_score = 1.0  # No essential requirements = full score

            # Elective Score (25% weight): what % of elective skills does candidate have?
            if elective_skills:
                elective_matched = candidate_skills.intersection(elective_skills)
                elective_score = len(elective_matched) / len(elective_skills)
            else:
                elective_matched = set()
                elective_score = 0.0  # No elective skills = no bonus

            # Combined keyword score
            if essential_skills and elective_skills:
                # If they have less than 50% of essential skills, ignore elective — all weight to essential
                if essential_score < 0.5:
                    keyword_score = essential_score
                else:
                    keyword_score = (essential_score * 0.75) + (elective_score * 0.25)
            elif essential_skills:
                keyword_score = essential_score  # 100% essential if no elective
            else:
                keyword_score = 0.0

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
            hybrid_score = (avg_semantic * 0.35) + (keyword_score * 0.35) + (exp_score * 0.30)
            
            # Build missing skills lists
            missing_essential = list(essential_skills - candidate_skills)
            missing_elective = list(elective_skills - candidate_skills)
            matched_essential = list(essential_matched)
            matched_elective = list(elective_matched)
            
            ranked_candidates.append({
                "candidate_id": file_id,
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(avg_semantic * 100, 2),
                "keyword_score": round(keyword_score * 100, 2),
                "essential_score": round(essential_score * 100, 2),
                "elective_score": round(elective_score * 100, 2),
                "experience_score": round(exp_score * 100, 2),
                "required_experience": required_exp,
                "candidate_experience": candidate_exp,
                "experience_gap": experience_gap,
                "matched_essential_skills": matched_essential,
                "matched_elective_skills": matched_elective,
                "missing_essential_skills": missing_essential,
                "missing_elective_skills": missing_elective,
                "extracted_skills": list(candidate_skills)
            })
            
        # Sort by hybrid match_score descending
        ranked_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        
        jd_skills_output = {
            "essential": list(essential_skills),
            "elective": list(elective_skills)
        }
        return ranked_candidates[:top_k], jd_skills_output
