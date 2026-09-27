from .VectorDBController import VectorDBController
from .EmbeddingController import EmbeddingController
from .ExtractionController import ExtractionController
from typing import List, Dict, Any

class MatchController:
    """
    Implements the Hybrid Ranking Engine: 
    Calculates Semantic Score (Cosine) and Keyword Score (Jaccard)
    with a 60% Semantic / 40% Keyword weighting.
    """
    def __init__(self):
        self.vector_db = VectorDBController()
        self.embedding = EmbeddingController()
        self.extraction = ExtractionController()
        
    def match_candidates(self, job_description: str, project_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # 1. Extract JD requirements and create embedding
        jd_skills = set(self.extraction.extract_skills(job_description))
        jd_embedding = self.embedding.embed_text(job_description)
        
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
                    "skills": set()
                }
            
            # Keep track of chunk scores
            candidates[file_id]["semantic_scores"].append(res["score"])
            
            # Aggregate skills extracted from candidate chunks
            chunk_skills = res["metadata"].get("skills", "")
            if chunk_skills:
                for skill in chunk_skills.split(","):
                    candidates[file_id]["skills"].add(skill.strip().lower())
                    
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
                
            # Weighted Hybrid Score: 60% Semantic / 40% Keyword
            hybrid_score = (avg_semantic * 0.6) + (jaccard * 0.4)
            
            missing_skills = list(jd_skills - candidate_skills)
            
            ranked_candidates.append({
                "candidate_id": file_id,
                "match_score": round(hybrid_score * 100, 2),
                "semantic_score": round(avg_semantic * 100, 2),
                "keyword_score": round(jaccard * 100, 2),
                "extracted_skills": list(candidate_skills),
                "missing_skills": missing_skills
            })
            
        # Sort by hybrid match_score descending
        ranked_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked_candidates[:top_k]
