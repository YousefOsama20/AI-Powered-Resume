"""
MatchController
───────────────
Implements the Hybrid Ranking Engine:
Semantic Score + Keyword Score + Experience Score + Job Type + Job Function.

Skills are classified into Essential and Elective.
"""

import logging
import numpy as np
from sqlalchemy.orm import Session
from .VectorDBController import VectorDBController, CANDIDATE_COLLECTION
from .EmbeddingController import EmbeddingController
from .ExtractionController import ExtractionController
from .ExperienceController import ExperienceController
from .LLMExtractionController import LLMExtractionController
from .JDController import JDController, JD_COLLECTION
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
                               jd_name: str = None, top_k: int = 5, company_id: str = None) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """
        Matches a job description against ALL candidates in the global pool and ranks them.
        Returns the top_k candidates (one row per customer, best CV kept).
        | Target: Company
        """
        try:
            top_k = int(top_k or 5)
        except (ValueError, TypeError):
            top_k = 5
        top_k = max(1, min(top_k, 50))

        essential_skills = set()
        elective_skills = set()
        required_exp = 0.0
        jd_embedding = None

        # Fetch JD ownership scoped by company so duplicate jd_names across
        # companies never leak into each other's matches.
        jd_sql = None
        if jd_name:
            if company_id:
                jd_sql = db.query(JobDescription).filter_by(jd_name=jd_name, company_id=company_id).first()
            if jd_sql is None:
                jd_sql = db.query(JobDescription).filter_by(jd_name=jd_name).first()
        jd_type_id = jd_sql.job_type_id if jd_sql else None
        jd_function_id = jd_sql.job_function_id if jd_sql else None

        if jd_name:
            stored_jd = self.jd_controller.get_jd(jd_name, company_id=company_id)
            if stored_jd:
                skills_data = stored_jd.get("skills", {})
                essential_skills = set(s for s in skills_data.get("essential", []) if s)
                elective_skills = set(s for s in skills_data.get("elective", []) if s)
                required_exp = stored_jd.get("required_experience", 0.0) or 0.0
                jd_embedding = stored_jd.get("embedding")
            
        if jd_embedding is None or len(jd_embedding) == 0:
            if not job_description:
                return [], {}
            
            classified = {"essential": [], "elective": []}
            if self.llm_extraction.is_available:
                try:
                    result = self.llm_extraction.extract_skills_from_jd(job_description)
                    if isinstance(result, dict):
                        classified = result
                except Exception as e:
                    logger.warning(f"[MatchController] LLM JD extraction failed, fallback: {e}")
            if not classified.get("essential") and not classified.get("elective"):
                try:
                    classified = self.extraction.extract_classified_skills(job_description)
                except Exception as e:
                    logger.warning(f"[MatchController] heuristic JD extraction failed: {e}")
                    classified = {"essential": [], "elective": []}
            essential_skills = set(
                s.strip().lower() for s in classified.get("essential", [])
                if isinstance(s, str) and s.strip()
            )
            elective_skills = set(
                s.strip().lower() for s in classified.get("elective", [])
                if isinstance(s, str) and s.strip()
            )
            elective_skills = {s for s in elective_skills if s not in essential_skills}

            jd_embedding = self.embedding.embed_text(job_description)
            required_exp = self.experience.extract_required_experience(job_description) or 0.0
        
        if not jd_embedding:
            return [], {}

        # Canonicalized copies for skill matching (aliases, plurals, case).
        # Originals are preserved for display in jd_skills_output.
        try:
            from .SkillNormalizer import (
                normalize_skill_list as _canon_list,
                match_skills as _match_skills,
                score_from_matches as _score_matches,
            )
            essential_norm = set(_canon_list(list(essential_skills)))
            elective_norm = set(_canon_list(list(elective_skills)))
            # Elective never duplicates essential after canonicalization.
            elective_norm = {s for s in elective_norm if s not in essential_norm}
            _use_normalizer = True
        except Exception:
            essential_norm = {str(s).strip().lower() for s in essential_skills if str(s).strip()}
            elective_norm = {str(s).strip().lower() for s in elective_skills if str(s).strip()}
            _use_normalizer = False

        # Query enough chunks to cover the WHOLE pool, not just the top-100.
        # Previously n_results=100 meant a single long CV could saturate the
        # results and only 1 candidate was ever ranked.
        try:
            total_chunks = self.vector_db.get_collection_count(CANDIDATE_COLLECTION)
        except Exception:
            total_chunks = 0
        n_results = max(100, int(total_chunks or 0), top_k * 20)
        # Chroma caps per-query results; keep it bounded but global.
        n_results = min(n_results, 5000)
             
        results = self.vector_db.search(
            query_embedding=jd_embedding,
            customer_id=customer_id,
            n_results=n_results,
            collection_name=CANDIDATE_COLLECTION
        )
        
        if not results:
            return [], {}
            
        candidates = {}
        for res in results:
            meta = res.get("metadata") or {}
            file_id = meta.get("file_id")
            cust_id = meta.get("customer_id", "")
            if not file_id or not cust_id:
                continue
                
            if file_id not in candidates:
                candidates[file_id] = {
                    "customer_id": cust_id,
                    "file_id": file_id,
                    "semantic_scores": [],
                    "skills": set(),
                    "experience_chunks_text": [],
                    "experience_years_fallback": 0.0
                }
            
            candidates[file_id]["semantic_scores"].append(res["score"])
            
            chunk_skills = meta.get("skills", "")
            if chunk_skills:
                for skill in chunk_skills.split(","):
                    try:
                        from .SkillNormalizer import normalize_skill as _canon_one
                        s = _canon_one(skill)
                    except Exception:
                        s = skill.strip().lower()
                    if s:
                        candidates[file_id]["skills"].add(s)

            if meta.get("section") == "Experience":
                chunk_text = res.get("document", "")
                if chunk_text:
                    candidates[file_id]["experience_chunks_text"].append(chunk_text)
                chunk_exp = meta.get("experience_years", 0)
                if isinstance(chunk_exp, (int, float)):
                    candidates[file_id]["experience_years_fallback"] = max(
                        candidates[file_id]["experience_years_fallback"], float(chunk_exp)
                    )

        logger.info(f"[MatchController] Chunks retrieved={len(results)}, distinct files={len(candidates)}")
                    
        ranked_candidates = []

        for file_id, data in candidates.items():
            if not data["semantic_scores"]:
                continue
            avg_semantic = sum(data["semantic_scores"]) / len(data["semantic_scores"])
            candidate_skills = data["skills"]

            # Keyword Score: canonical + fuzzy matching (rest apis == rest api).
            if _use_normalizer:
                matched_ess, missing_ess, _ = _match_skills(candidate_skills, essential_norm)
                matched_ele, missing_ele, _ = _match_skills(candidate_skills, elective_norm)
                essential_matched = set(matched_ess)
                elective_matched = set(matched_ele)
                keyword_score, essential_score, elective_score = _score_matches(
                    matched_ess, len(essential_norm), matched_ele, len(elective_norm)
                )
            else:
                # Legacy exact-match fallback
                if essential_norm:
                    essential_matched = candidate_skills.intersection(essential_norm)
                    essential_score = len(essential_matched) / len(essential_norm)
                else:
                    essential_matched = set()
                    essential_score = 1.0

                if elective_norm:
                    elective_matched = candidate_skills.intersection(elective_norm)
                    elective_score = len(elective_matched) / len(elective_norm)
                else:
                    elective_matched = set()
                    elective_score = 0.0

                if essential_norm and elective_norm:
                    if essential_score < 0.5:
                        keyword_score = essential_score
                    else:
                        keyword_score = (essential_score * 0.75) + (elective_score * 0.25)
                elif essential_norm:
                    keyword_score = essential_score
                else:
                    keyword_score = 0.0

            # Experience Score
            combined_exp_text = "\n\n".join(data["experience_chunks_text"])
            candidate_exp = self.experience.extract_candidate_experience(combined_exp_text)
            if candidate_exp == 0.0:
                candidate_exp = data["experience_years_fallback"]
            req_exp = float(required_exp or 0.0)
            exp_score = self.experience.calculate_experience_score(req_exp if req_exp > 0 else None, candidate_exp)

            experience_gap = round(req_exp - candidate_exp, 1) if (req_exp and candidate_exp < req_exp) else 0

            # Database Enrichment (Type, Function)
            type_score = 0.0
            func_score = 0.0

            profile = db.query(CustomerProfile).filter_by(id=data["customer_id"]).first()
            if profile and jd_sql:
                # Job Type
                profile_types = [t.id for t in profile.job_types]
                if not jd_type_id or jd_type_id in profile_types:
                    type_score = 1.0

                # Job Function
                profile_funcs = [f.id for f in profile.job_functions]
                if not jd_function_id or jd_function_id in profile_funcs:
                    func_score = 1.0

            # Weighted Hybrid Score: 30% Semantic, 30% Keyword, 20% Exp, 10% Type, 10% Func
            hybrid_score = (avg_semantic * 0.30) + (keyword_score * 0.30) + (exp_score * 0.20) + (type_score * 0.10) + (func_score * 0.10)
            
            if _use_normalizer:
                missing_essential = sorted(missing_ess)
                missing_elective = sorted(missing_ele)
                matched_essential = sorted(matched_ess)
                matched_elective = sorted(matched_ele)
            else:
                missing_essential = list(essential_norm - candidate_skills)
                missing_elective = list(elective_norm - candidate_skills)
                matched_essential = list(essential_matched)
                matched_elective = list(elective_matched)
            
            ranked_candidates.append({
                "candidate_id": file_id,
                "file_id": file_id,
                "customer_id": data["customer_id"],
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(avg_semantic * 100, 2),
                "keyword_score": round(keyword_score * 100, 2),
                "essential_score": round(essential_score * 100, 2),
                "elective_score": round(elective_score * 100, 2),
                "experience_score": round(exp_score * 100, 2),
                "job_type_score": round(type_score * 100, 2),
                "job_function_score": round(func_score * 100, 2),
                "required_experience": req_exp,
                "candidate_experience": candidate_exp,
                "experience_gap": experience_gap,
                "matched_essential_skills": matched_essential,
                "matched_elective_skills": matched_elective,
                "missing_essential_skills": missing_essential,
                "missing_elective_skills": missing_elective,
                "extracted_skills": list(candidate_skills)
            })
            
        ranked_candidates.sort(key=lambda x: x["match_score"], reverse=True)

        # Collapse to one row per customer (best CV wins) so a candidate with
        # multiple uploads doesn't crowd out the rest of the pool, while still
        # covering every customer found in the vector search.
        best_by_customer: Dict[str, Dict[str, Any]] = {}
        for entry in ranked_candidates:
            cid = entry.get("customer_id") or entry.get("candidate_id")
            existing = best_by_customer.get(cid)
            if existing is None or entry["match_score"] > existing["match_score"]:
                best_by_customer[cid] = entry
        ranked_unique = sorted(best_by_customer.values(), key=lambda x: x["match_score"], reverse=True)
        logger.info(f"[MatchController] Files ranked={len(ranked_candidates)}, unique candidates={len(ranked_unique)}, returning top_k={top_k}")
        
        jd_skills_output = {
            "essential": list(essential_skills),
            "elective": list(elective_skills)
        }
        
        return ranked_unique[:top_k], jd_skills_output

    def recommend_jobs(self, db: Session, document_id: str, top_k: int = 5,
                         job_type_ids: List[str] = None,
                         job_function_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Recommends JDs for a specific candidate document by reverse-matching.
        | Target: Customer

        Optional multi-select filters (server-side):
        - job_type_ids: only return JDs whose job_type_id is in this set.
          JDs with NULL job_type_id are excluded when a filter is active
          (they still appear under "All").
        - job_function_ids: same semantics for job_function_id.
        """
        doc = db.query(CandidateDocument).filter_by(id=document_id).first()
        if not doc:
            return []

        profile = doc.customer

        # Normalize filter sets (drop empties).
        type_filter = {str(v).strip() for v in (job_type_ids or []) if str(v).strip()}
        func_filter = {str(v).strip() for v in (job_function_ids or []) if str(v).strip()}
        has_filter = bool(type_filter or func_filter)
        
        # 1. Fetch Candidate Embeddings
        collection = self.vector_db._get_collection(CANDIDATE_COLLECTION)
        data = collection.get(where={"file_id": doc.vector_id}, include=["embeddings", "metadatas"])
        
        if not data or data.get("embeddings") is None or len(data.get("embeddings")) == 0:
            return []
            
        # Average the embeddings to get a single vector representing the CV
        embeddings = np.array(data["embeddings"])
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        
        # Collect candidate skills from metadata (canonicalized).
        candidate_skills = set()
        candidate_exp = 0.0
        try:
            from .SkillNormalizer import normalize_skill as _canon_one2
            _has_canon = True
        except Exception:
            _has_canon = False
        for meta in data.get("metadatas", []):
            if meta.get("skills"):
                for s in meta.get("skills").split(","):
                    if _has_canon:
                        v = _canon_one2(s)
                    else:
                        v = s.strip().lower()
                    if v:
                        candidate_skills.add(v)
            if meta.get("section") == "Experience" and meta.get("experience_years"):
                candidate_exp = max(candidate_exp, float(meta.get("experience_years", 0)))
                
        # 2. Search Job Descriptions
        jd_collection = self.vector_db._get_collection(JD_COLLECTION)
        # When filters are active, fetch extra candidates so post-filtering
        # still fills top_k (filtering happens after re-rank, below).
        n_fetch = (top_k * 5 if has_filter else top_k * 3)
        n_fetch = max(1, min(n_fetch, 250))
        results = jd_collection.query(
            query_embeddings=[avg_embedding],
            n_results=n_fetch # Fetch extra for re-ranking
        )
        
        if not results or not results["ids"] or len(results["ids"][0]) == 0:
            logger.error(f"[MatchController] No JDs found in ChromaDB: {results}")
            return []
            
        jds_found = results["ids"][0]
        distances = results["distances"][0]
        
        ranked_jobs = []
        seen_jd_ids = set()
        for i in range(len(jds_found)):
            chroma_jd_id = jds_found[i]
            semantic_score = max(0, 1.0 - distances[i]) # Cosine distance to similarity

            # Chroma ids are company-scoped ({company_id}::{jd_name}) for new
            # JDs, bare jd_name for legacy ones.
            jd_company_id = None
            jd_name = chroma_jd_id
            if "::" in chroma_jd_id:
                jd_company_id, jd_name = chroma_jd_id.split("::", 1)
            
            jd_sql = None
            if jd_company_id:
                jd_sql = db.query(JobDescription).filter_by(jd_name=jd_name, company_id=jd_company_id).first()
            if jd_sql is None:
                jd_sql = db.query(JobDescription).filter_by(jd_name=jd_name).first()
            if not jd_sql or jd_sql.is_public == 0:
                logger.error(f"[MatchController] JD {chroma_jd_id} SQL check failed (is_public={jd_sql.is_public if jd_sql else None})")
                continue
            # Server-side multi-select filtering by taxonomy.
            if type_filter and (not jd_sql.job_type_id or str(jd_sql.job_type_id) not in type_filter):
                continue
            if func_filter and (not jd_sql.job_function_id or str(jd_sql.job_function_id) not in func_filter):
                continue
            if jd_sql.id in seen_jd_ids:
                continue
            seen_jd_ids.add(jd_sql.id)
                 
            jd_data = self.jd_controller.get_jd(jd_name, company_id=jd_sql.company_id)
            if not jd_data:
                continue
                
            essential = set()
            elective = set()
            try:
                from .SkillNormalizer import (
                    normalize_skill_list as _canon_list2,
                    match_skills as _match_skills2,
                    score_from_matches as _score2,
                )
                essential = set(_canon_list2(jd_data.get("skills", {}).get("essential", [])))
                elective = set(_canon_list2(jd_data.get("skills", {}).get("elective", [])))
                elective = {s for s in elective if s not in essential}
                required_exp = jd_data.get("required_experience", 0.0) or 0.0

                # Keyword Score: canonical + fuzzy (75/25 + strict mode).
                matched_ess2, missing_ess2, _ = _match_skills2(candidate_skills, essential)
                matched_ele2, missing_ele2, _ = _match_skills2(candidate_skills, elective)
                keyword_score, essential_score, elective_score = _score2(
                    matched_ess2, len(essential), matched_ele2, len(elective)
                )
                _norm_ok = True
            except Exception:
                essential = {str(s).strip().lower() for s in jd_data.get("skills", {}).get("essential", []) if str(s).strip()}
                elective = {str(s).strip().lower() for s in jd_data.get("skills", {}).get("elective", []) if str(s).strip()}
                elective = {s for s in elective if s not in essential}
                required_exp = jd_data.get("required_experience", 0.0) or 0.0

                # Keyword Score: same 75/25 essential/elective weighting as
                # match_candidates, with strict mode (elective ignored when the
                # candidate covers <50% of essentials).
                if essential:
                    essential_matched = candidate_skills.intersection(essential)
                    essential_score = len(essential_matched) / len(essential)
                else:
                    essential_matched = set()
                    essential_score = 1.0
                if elective:
                    elective_matched = candidate_skills.intersection(elective)
                    elective_score = len(elective_matched) / len(elective)
                else:
                    elective_matched = set()
                    elective_score = 0.0
                if essential and elective:
                    if essential_score < 0.5:
                        keyword_score = essential_score
                    else:
                        keyword_score = (essential_score * 0.75) + (elective_score * 0.25)
                elif essential:
                    keyword_score = essential_score
                else:
                    keyword_score = 0.0
                matched_ess2 = sorted(essential_matched) if essential else []
                missing_ess2 = sorted(essential - candidate_skills) if essential else []
                matched_ele2 = sorted(elective_matched) if elective else []
                missing_ele2 = sorted(elective - candidate_skills) if elective else []
                _norm_ok = False
                
            # Experience Score
            exp_score = self.experience.calculate_experience_score(required_exp if required_exp > 0 else None, candidate_exp)
            
            # Enrich Scores
            type_score = 0.0
            func_score = 0.0

            profile_types = [t.id for t in profile.job_types]
            if not jd_sql.job_type_id or jd_sql.job_type_id in profile_types:
                type_score = 1.0
                
            profile_funcs = [f.id for f in profile.job_functions]
            if not jd_sql.job_function_id or jd_sql.job_function_id in profile_funcs:
                func_score = 1.0
                
            hybrid_score = (semantic_score * 0.30) + (keyword_score * 0.30) + (exp_score * 0.20) + (type_score * 0.10) + (func_score * 0.10)
            
            ranked_jobs.append({
                "jd_id": jd_sql.id,
                "jd_name": jd_sql.jd_name,
                "company_name": jd_sql.company.company_name if jd_sql.company else "Unknown",
                "location": jd_sql.location,
                "job_type": {"id": jd_sql.job_type.id, "name": jd_sql.job_type.name} if getattr(jd_sql, "job_type", None) else None,
                "job_function": {"id": jd_sql.job_function.id, "name": jd_sql.job_function.name} if getattr(jd_sql, "job_function", None) else None,
                "created_at": jd_sql.created_at.isoformat() if getattr(jd_sql, "created_at", None) else None,
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(semantic_score * 100, 2),
                "keyword_score": round(keyword_score * 100, 2),
                "essential_score": round(essential_score * 100, 2),
                "elective_score": round(elective_score * 100, 2),
                "experience_score": round(exp_score * 100, 2),
                "job_type_score": round(type_score * 100, 2),
                "job_function_score": round(func_score * 100, 2),
                "required_experience": required_exp,
                "essential_skills": sorted(essential),
                "elective_skills": sorted(elective),
                "matched_essential_skills": sorted(matched_ess2),
                "missing_essential_skills": sorted(missing_ess2),
                "matched_elective_skills": sorted(matched_ele2),
                "missing_elective_skills": sorted(missing_ele2),
                "candidate_skills": sorted(candidate_skills),
            })
            
        ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked_jobs[:top_k]
