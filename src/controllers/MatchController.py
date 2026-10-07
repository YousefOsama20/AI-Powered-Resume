"""
MatchController
───────────────
Implements the Hybrid Ranking Engine:
Semantic Score + Keyword Score + Experience Score + Location + Job Type + Job Function.

Skills are classified into Essential and Elective.
"""

import logging
import numpy as np
from sqlalchemy.orm import Session
from .VectorDBController import VectorDBController
from .EmbeddingController import EmbeddingController
from .ExtractionController import ExtractionController
from .ExperienceController import ExperienceController
from .LLMExtractionController import LLMExtractionController
from .JDController import JDController
from typing import List, Dict, Any, Tuple

from models.sql_models import JobDescription, CustomerProfile, CandidateDocument, JobType, JobFunction

logger = logging.getLogger("uvicorn.error")

class MatchController:
    """
    Implements the Hybrid Ranking Engine for Company-side Match and Candidate-side Job Recommendations.
    """
    def __init__(self):
        """Initializes MatchController and sub-controllers."""
        self.vector_db = VectorDBController()
        self.embedding = EmbeddingController()
        self.extraction = ExtractionController()
        self.experience = ExperienceController()
        self.llm_extraction = LLMExtractionController()
        self.jd_controller = JDController()
        
    def match_candidates(self, db: Session, customer_id: str = None, job_description: str = None, 
                               jd_name: str = None, top_k: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """
        Matches a job description against candidates and ranks them.
        | Target: Company
        """
        essential_skills = set()
        elective_skills = set()
        required_exp = 0.0
        jd_embedding = None

        # Try fetching JD details from SQL
        jd_sql = db.query(JobDescription).filter_by(jd_name=jd_name).first() if jd_name else None
        jd_location = jd_sql.location if jd_sql else None
        jd_type_id = jd_sql.job_type_id if jd_sql else None
        jd_function_id = jd_sql.job_function_id if jd_sql else None

        if jd_name:
            stored_jd = self.jd_controller.get_jd(jd_name)
            if stored_jd:
                skills_data = stored_jd.get("skills", {})
                essential_skills = set(skills_data.get("essential", []))
                elective_skills = set(skills_data.get("elective", []))
                required_exp = stored_jd.get("required_experience", 0.0)
                jd_embedding = stored_jd.get("embedding")
            
        if jd_embedding is None or len(jd_embedding) == 0:
            if not job_description:
                return [], {}
            
            if self.llm_extraction.is_available:
                classified = self.llm_extraction.extract_skills_from_jd(job_description)
                essential_skills = set(classified.get("essential", []))
                elective_skills = set(classified.get("elective", []))
            else:
                essential_skills = set(self.extraction.extract_skills(job_description))

            jd_embedding = self.embedding.embed_text(job_description)
            required_exp = self.experience.extract_required_experience(job_description)
        
        if not jd_embedding:
            return [], {}
            
        results = self.vector_db.search(
            query_embedding=jd_embedding,
            customer_id=customer_id,
            n_results=100
        )
        
        if not results:
            return [], {}
            
        candidates = {}
        for res in results:
            file_id = res["metadata"].get("file_id")
            if not file_id:
                continue
                
            if file_id not in candidates:
                candidates[file_id] = {
                    "customer_id": res["metadata"].get("customer_id", ""),
                    "semantic_scores": [],
                    "skills": set(),
                    "experience_chunks_text": [],
                    "experience_years_fallback": 0.0
                }
            
            candidates[file_id]["semantic_scores"].append(res["score"])
            
            chunk_skills = res["metadata"].get("skills", "")
            if chunk_skills:
                for skill in chunk_skills.split(","):
                    candidates[file_id]["skills"].add(skill.strip().lower())

            if res["metadata"].get("section") == "Experience":
                chunk_text = res.get("document", "")
                if chunk_text:
                    candidates[file_id]["experience_chunks_text"].append(chunk_text)
                chunk_exp = res["metadata"].get("experience_years", 0)
                if isinstance(chunk_exp, (int, float)):
                    candidates[file_id]["experience_years_fallback"] = max(
                        candidates[file_id]["experience_years_fallback"], float(chunk_exp)
                    )
                    
        all_jd_skills = essential_skills | elective_skills
        ranked_candidates = []

        for file_id, data in candidates.items():
            avg_semantic = sum(data["semantic_scores"]) / len(data["semantic_scores"])
            candidate_skills = data["skills"]

            # Keyword Score
            if essential_skills:
                essential_matched = candidate_skills.intersection(essential_skills)
                essential_score = len(essential_matched) / len(essential_skills)
            else:
                essential_matched = set()
                essential_score = 1.0

            if elective_skills:
                elective_matched = candidate_skills.intersection(elective_skills)
                elective_score = len(elective_matched) / len(elective_skills)
            else:
                elective_matched = set()
                elective_score = 0.0

            if essential_skills and elective_skills:
                if essential_score < 0.5:
                    keyword_score = essential_score
                else:
                    keyword_score = (essential_score * 0.75) + (elective_score * 0.25)
            elif essential_skills:
                keyword_score = essential_score
            else:
                keyword_score = 0.0

            # Experience Score
            combined_exp_text = "\n\n".join(data["experience_chunks_text"])
            candidate_exp = self.experience.extract_candidate_experience(combined_exp_text)
            if candidate_exp == 0.0:
                candidate_exp = data["experience_years_fallback"]
            exp_score = self.experience.calculate_experience_score(required_exp, candidate_exp)

            experience_gap = round(required_exp - candidate_exp, 1) if (required_exp and candidate_exp < required_exp) else 0

            # Database Enrichment (Location, Type, Function)
            loc_score = 0.0
            type_score = 0.0
            func_score = 0.0
            
            profile = db.query(CustomerProfile).filter_by(id=data["customer_id"]).first()
            if profile and jd_sql:
                # Location (Exact Match or Not provided = 1.0)
                if not jd_location or not profile.location or jd_location.lower() == profile.location.lower():
                    loc_score = 1.0
                
                # Job Type
                profile_types = [t.id for t in profile.job_types]
                if not jd_type_id or jd_type_id in profile_types:
                    type_score = 1.0
                    
                # Job Function
                profile_funcs = [f.id for f in profile.job_functions]
                if not jd_function_id or jd_function_id in profile_funcs:
                    func_score = 1.0

            # Weighted Hybrid Score: 25% Semantic, 25% Keyword, 20% Exp, 10% Loc, 10% Type, 10% Func
            hybrid_score = (avg_semantic * 0.25) + (keyword_score * 0.25) + (exp_score * 0.20) + (loc_score * 0.10) + (type_score * 0.10) + (func_score * 0.10)
            
            missing_essential = list(essential_skills - candidate_skills)
            missing_elective = list(elective_skills - candidate_skills)
            matched_essential = list(essential_matched)
            matched_elective = list(elective_matched)
            
            ranked_candidates.append({
                "candidate_id": file_id,
                "customer_id": data["customer_id"],
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(avg_semantic * 100, 2),
                "keyword_score": round(keyword_score * 100, 2),
                "essential_score": round(essential_score * 100, 2),
                "elective_score": round(elective_score * 100, 2),
                "experience_score": round(exp_score * 100, 2),
                "location_score": round(loc_score * 100, 2),
                "job_type_score": round(type_score * 100, 2),
                "job_function_score": round(func_score * 100, 2),
                "required_experience": required_exp,
                "candidate_experience": candidate_exp,
                "experience_gap": experience_gap,
                "matched_essential_skills": matched_essential,
                "matched_elective_skills": matched_elective,
                "missing_essential_skills": missing_essential,
                "missing_elective_skills": missing_elective,
                "extracted_skills": list(candidate_skills)
            })
            
        ranked_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        
        jd_skills_output = {
            "essential": list(essential_skills),
            "elective": list(elective_skills)
        }
        
        return ranked_candidates[:top_k], jd_skills_output

    def recommend_jobs(self, db: Session, document_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Recommends JDs for a specific candidate document by reverse-matching.
        | Target: Customer
        """
        doc = db.query(CandidateDocument).filter_by(id=document_id).first()
        if not doc:
            return []
            
        profile = doc.customer
        
        # 1. Fetch Candidate Embeddings
        collection = self.vector_db._get_collection("candidates")
        data = collection.get(where={"file_id": doc.vector_id}, include=["embeddings", "metadatas"])
        
        if not data or data.get("embeddings") is None or len(data.get("embeddings")) == 0:
            return []
            
        # Average the embeddings to get a single vector representing the CV
        embeddings = np.array(data["embeddings"])
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        
        # Collect candidate skills from metadata
        candidate_skills = set()
        candidate_exp = 0.0
        for meta in data.get("metadatas", []):
            if meta.get("skills"):
                for s in meta.get("skills").split(","):
                    candidate_skills.add(s.strip().lower())
            if meta.get("section") == "Experience" and meta.get("experience_years"):
                candidate_exp = max(candidate_exp, float(meta.get("experience_years", 0)))
                
        # 2. Search Job Descriptions
        jd_collection = self.vector_db._get_collection("jds")
        results = jd_collection.query(
            query_embeddings=[avg_embedding],
            n_results=top_k * 3 # Fetch extra for re-ranking
        )
        
        if not results or not results["ids"] or len(results["ids"][0]) == 0:
            logger.error(f"[MatchController] No JDs found in ChromaDB: {results}")
            return []
            
        jds_found = results["ids"][0]
        distances = results["distances"][0]
        
        ranked_jobs = []
        for i in range(len(jds_found)):
            jd_name = jds_found[i]
            semantic_score = max(0, 1.0 - distances[i]) # Cosine distance to similarity
            
            jd_sql = db.query(JobDescription).filter_by(jd_name=jd_name).first()
            if not jd_sql or jd_sql.is_public == 0:
                logger.error(f"[MatchController] JD {jd_name} SQL check failed (is_public={jd_sql.is_public if jd_sql else None})")
                continue
                
            jd_data = self.jd_controller.get_jd(jd_name)
            if not jd_data:
                continue
                
            essential = set(jd_data.get("skills", {}).get("essential", []))
            required_exp = jd_data.get("required_experience", 0.0)
            
            # Keyword Score
            keyword_score = 1.0
            if essential:
                matched = candidate_skills.intersection(essential)
                keyword_score = len(matched) / len(essential)
                
            # Experience Score
            exp_score = self.experience.calculate_experience_score(required_exp, candidate_exp)
            
            # Enrich Scores
            loc_score = 0.0
            type_score = 0.0
            func_score = 0.0
            
            if not jd_sql.location or not profile.location or jd_sql.location.lower() == profile.location.lower():
                loc_score = 1.0
                
            profile_types = [t.id for t in profile.job_types]
            if not jd_sql.job_type_id or jd_sql.job_type_id in profile_types:
                type_score = 1.0
                
            profile_funcs = [f.id for f in profile.job_functions]
            if not jd_sql.job_function_id or jd_sql.job_function_id in profile_funcs:
                func_score = 1.0
                
            hybrid_score = (semantic_score * 0.25) + (keyword_score * 0.25) + (exp_score * 0.20) + (loc_score * 0.10) + (type_score * 0.10) + (func_score * 0.10)
            
            ranked_jobs.append({
                "jd_id": jd_sql.id,
                "jd_name": jd_sql.jd_name,
                "company_name": jd_sql.company.company_name if jd_sql.company else "Unknown",
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(semantic_score * 100, 2),
                "keyword_score": round(keyword_score * 100, 2),
                "experience_score": round(exp_score * 100, 2),
                "location_score": round(loc_score * 100, 2),
                "job_type_score": round(type_score * 100, 2),
                "job_function_score": round(func_score * 100, 2)
            })
            
        ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked_jobs[:top_k]
