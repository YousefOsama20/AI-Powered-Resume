"""
JDController
────────────
Handles storing and retrieving Job Descriptions directly in ChromaDB.
Stores classified skills (essential/elective) as separate metadata fields.
"""

import logging
from typing import Dict, Any, Optional, List

from .BaseController import BaseController
from .VectorDBController import VectorDBController

logger = logging.getLogger("uvicorn.error")

JD_COLLECTION = "jds"

class JDController(BaseController):
    
    def __init__(self):
        # Type: Sub-function
        super().__init__()
        self.vector_db = VectorDBController()

    def store_jd(self, jd_name: str, company_id: str, job_description: str,
                 skills: Dict[str, List[str]], required_exp: float,
                 embedding: list) -> bool:
        # Type: Main function
        """
        Stores a Job Description entirely in ChromaDB as a single document.
        Skills are stored as classified: essential_skills and elective_skills.
        Uses upsert to automatically overwrite if the jd_name already exists.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            
            essential = skills.get("essential", [])
            elective = skills.get("elective", [])
            
            # Upsert into ChromaDB
            collection.upsert(
                ids=[jd_name],
                documents=[job_description],
                embeddings=[embedding],
                metadatas=[{
                    "company_id": company_id,
                    "essential_skills": ",".join(essential),
                    "elective_skills": ",".join(elective),
                    "required_experience": float(required_exp)
                }]
            )
            
            logger.info(f"[JDController] Stored JD in ChromaDB: {jd_name} ({len(essential)} essential, {len(elective)} elective)")
            return True
        except Exception as e:
            logger.error(f"[JDController] Error storing JD in ChromaDB: {e}")
            return False

    def get_jd(self, jd_name: str, company_id: str = None) -> Optional[Dict[str, Any]]:
        # Type: Main function
        """
        Retrieves a stored Job Description and its metadata from ChromaDB.
        Returns skills as classified dict: {"essential": [...], "elective": [...]}.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            
            where_clause = None
            if company_id:
                where_clause = {"company_id": company_id}
                
            results = collection.get(
                ids=[jd_name],
                where=where_clause,
                include=["embeddings", "metadatas", "documents"]
            )
            
            if not results or not results["ids"]:
                return None
                
            meta = results["metadatas"][0]
            essential_str = meta.get("essential_skills", "")
            elective_str = meta.get("elective_skills", "")
            
            emb = results["embeddings"][0]
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
                
            return {
                "job_description": results["documents"][0],
                "skills": {
                    "essential": essential_str.split(",") if essential_str else [],
                    "elective": elective_str.split(",") if elective_str else []
                },
                "required_experience": meta.get("required_experience", 0.0),
                "embedding": emb
            }
        except Exception as e:
            logger.error(f"[JDController] Error retrieving JD from ChromaDB: {e}")
            return None

    def list_jds(self, company_id: str = None) -> list:
        # Type: Main function
        """
        Returns a list of all stored JD names with their classified skills and experience.
        Optionally filters by company_id.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            
            where_clause = None
            if company_id:
                where_clause = {"company_id": company_id}
                
            results = collection.get(
                where=where_clause,
                include=["metadatas"]
            )
            
            jds = []
            if results and results["ids"]:
                for i in range(len(results["ids"])):
                    jd_name = results["ids"][i]
                    meta = results["metadatas"][i]
                    essential_str = meta.get("essential_skills", "")
                    elective_str = meta.get("elective_skills", "")
                    essential_list = essential_str.split(",") if essential_str else []
                    elective_list = elective_str.split(",") if elective_str else []
                    
                    jds.append({
                        "jd_name": jd_name,
                        "company_id": meta.get("company_id", ""),
                        "essential_skills_count": len(essential_list),
                        "elective_skills_count": len(elective_list),
                        "total_skills_count": len(essential_list) + len(elective_list),
                        "required_experience": meta.get("required_experience", 0.0),
                        "essential_skills": essential_list,
                        "elective_skills": elective_list
                    })
            return jds
        except Exception as e:
            logger.error(f"[JDController] Error listing JDs from ChromaDB: {e}")
            return []

    def delete_jd(self, jd_name: str, company_id: str = None) -> bool:
        # Type: Main function
        """Deletes a JD from ChromaDB. Optionally verifies company ownership."""
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            
            where_clause = None
            if company_id:
                where_clause = {"company_id": company_id}
                
            collection.delete(
                ids=[jd_name],
                where=where_clause
            )
            logger.info(f"[JDController] Deleted JD from ChromaDB: {jd_name}")
            return True
        except Exception as e:
            logger.error(f"[JDController] Error deleting JD from ChromaDB: {e}")
            return False
