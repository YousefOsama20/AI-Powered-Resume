"""
JDController
────────────
Handles storing and retrieving Job Descriptions directly in ChromaDB.
Eliminates the need for a separate JSON file.
"""

import logging
from typing import Dict, Any, Optional

from .BaseController import BaseController
from .VectorDBController import VectorDBController

logger = logging.getLogger("uvicorn.error")

JD_COLLECTION = "jds"

class JDController(BaseController):
    
    def __init__(self):
        # Type: Sub-function
        super().__init__()
        self.vector_db = VectorDBController()

    def store_jd(self, jd_name: str, job_description: str, skills: list, required_exp: float, embedding: list) -> bool:
        # Type: Main function
        """
        Stores a Job Description entirely in ChromaDB as a single document.
        Uses upsert to automatically overwrite if the jd_name already exists.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            
            # Upsert into ChromaDB
            collection.upsert(
                ids=[jd_name],
                documents=[job_description],
                embeddings=[embedding],
                metadatas=[{
                    "skills": ",".join(skills),
                    "required_experience": float(required_exp)
                }]
            )
            
            logger.info(f"[JDController] Successfully stored JD in ChromaDB: {jd_name}")
            return True
        except Exception as e:
            logger.error(f"[JDController] Error storing JD in ChromaDB: {e}")
            return False

    def get_jd(self, jd_name: str) -> Optional[Dict[str, Any]]:
        # Type: Main function
        """
        Retrieves a stored Job Description and its metadata from ChromaDB.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            results = collection.get(
                ids=[jd_name],
                include=["embeddings", "metadatas", "documents"]
            )
            
            if not results or not results["ids"]:
                return None
                
            meta = results["metadatas"][0]
            skills_str = meta.get("skills", "")
            
            emb = results["embeddings"][0]
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
                
            return {
                "job_description": results["documents"][0],
                "skills": skills_str.split(",") if skills_str else [],
                "required_experience": meta.get("required_experience", 0.0),
                "embedding": emb
            }
        except Exception as e:
            logger.error(f"[JDController] Error retrieving JD from ChromaDB: {e}")
            return None

    def list_jds(self) -> list:
        # Type: Main function
        """
        Returns a list of all stored JD names with their skills and experience from ChromaDB.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            # Only need metadata to list them
            results = collection.get(include=["metadatas"])
            
            jds = []
            if results and results["ids"]:
                for i in range(len(results["ids"])):
                    jd_name = results["ids"][i]
                    meta = results["metadatas"][i]
                    skills_str = meta.get("skills", "")
                    skills_list = skills_str.split(",") if skills_str else []
                    
                    jds.append({
                        "jd_name": jd_name,
                        "skills_count": len(skills_list),
                        "required_experience": meta.get("required_experience", 0.0),
                        "skills": skills_list
                    })
            return jds
        except Exception as e:
            logger.error(f"[JDController] Error listing JDs from ChromaDB: {e}")
            return []

    def delete_jd(self, jd_name: str) -> bool:
        # Type: Main function
        """Deletes a JD from ChromaDB."""
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)
            collection.delete(ids=[jd_name])
            logger.info(f"[JDController] Deleted JD from ChromaDB: {jd_name}")
            return True
        except Exception as e:
            logger.error(f"[JDController] Error deleting JD from ChromaDB: {e}")
            return False
