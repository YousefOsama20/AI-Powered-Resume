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

    @staticmethod
    def _chroma_id(jd_name: str, company_id: str = None) -> str:
        """Company-scoped Chroma ID so two companies can reuse the same jd_name.

        Legacy JDs were stored under bare ``jd_name``; new writes use
        ``{company_id}::{jd_name}``. Readers try the scoped id first and fall
        back to the legacy id for backward compatibility.
        """
        if company_id:
            return f"{company_id}::{jd_name}"
        return jd_name

    @staticmethod
    def _display_name(chroma_id: str, metadata: dict) -> str:
        if isinstance(metadata, dict) and metadata.get("jd_name"):
            return metadata.get("jd_name")
        if "::" in chroma_id:
            return chroma_id.split("::", 1)[1]
        return chroma_id

    @staticmethod
    def _parse_skill_string(raw) -> list:
        """Parse a stored skills value (comma-string, JSON list-string, or list)."""
        import json as _json
        if raw is None:
            return []
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, str):
            text = raw.strip()
            if not text:
                return []
            # Legacy JSON-encoded list: '["python", "sql"]'
            if text.startswith("["):
                try:
                    parsed = _json.loads(text)
                    items = parsed if isinstance(parsed, list) else [text]
                except Exception:
                    items = [s for s in text.strip("[]").split(",")]
            else:
                items = text.split(",")
        else:
            return []
        seen = set()
        out = []
        for s in items:
            if isinstance(s, str):
                try:
                    from .SkillNormalizer import normalize_skill as _canon_one
                    v = _canon_one(s)
                except Exception:
                    v = s.strip().lower().strip("\"'")
                if v and v not in seen:
                    seen.add(v)
                    out.append(v)
        return out

    def store_jd(self, jd_name: str, company_id: str, job_description: str,
                 skills: Dict[str, List[str]], required_exp: float,
                 embedding: list) -> bool:
        # Type: Main function
        """
        Stores a Job Description entirely in ChromaDB as a single document.
        Skills are stored as classified: essential_skills and elective_skills.
        Uses upsert to automatically overwrite if the jd_name already exists.
        Chroma id is company-scoped so identical jd_names from different
        companies never overwrite each other.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)

            essential = self._parse_skill_string((skills or {}).get("essential", []))
            elective = self._parse_skill_string((skills or {}).get("elective", []))
            # Elective must never duplicate essential (LLM sometimes repeats).
            essential_set = set(essential)
            elective = [s for s in elective if s not in essential_set]
            
            chroma_id = self._chroma_id(jd_name, company_id)
            # Upsert into ChromaDB
            collection.upsert(
                ids=[chroma_id],
                documents=[job_description],
                embeddings=[embedding],
                metadatas=[{
                    "company_id": company_id,
                    "jd_name": jd_name,
                    "essential_skills": ",".join(essential),
                    "elective_skills": ",".join(elective),
                    "required_experience": float(required_exp or 0.0)
                }]
            )
            
            logger.info(f"[JDController] Stored JD in ChromaDB: {chroma_id} ({len(essential)} essential, {len(elective)} elective)")
            return True
        except Exception as e:
            logger.error(f"[JDController] Error storing JD in ChromaDB: {e}")
            return False

    def get_jd(self, jd_name: str, company_id: str = None) -> Optional[Dict[str, Any]]:
        # Retrieve a single JD with its skills and metadata from ChromaDB. | Company
        # Type: Main function
        """
        Retrieves a stored Job Description and its metadata from ChromaDB.
        Returns skills as classified dict: {"essential": [...], "elective": [...]}.
        Tries the company-scoped id first, then falls back to the legacy bare
        jd_name id for JDs stored before scoping was introduced.
        """
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)

            candidates = []
            if company_id:
                candidates.append(self._chroma_id(jd_name, company_id))
            candidates.append(jd_name)
            
            for chroma_id in candidates:
                where_clause = {"company_id": company_id} if company_id else None
                try:
                    results = collection.get(
                        ids=[chroma_id],
                        where=where_clause,
                        include=["embeddings", "metadatas", "documents"]
                    )
                except Exception:
                    # Some Chroma versions reject ids+where combos; retry ids-only.
                    results = collection.get(
                        ids=[chroma_id],
                        include=["embeddings", "metadatas", "documents"]
                    )
                    if results and results.get("metadatas"):
                        meta_check = results["metadatas"][0] or {}
                        if company_id and meta_check.get("company_id") != company_id:
                            continue
                
                if not results or not results["ids"]:
                    continue
                    
                meta = results["metadatas"][0] or {}
                if company_id and meta.get("company_id") and meta.get("company_id") != company_id:
                    continue
                essential = self._parse_skill_string(meta.get("essential_skills", ""))
                elective = self._parse_skill_string(meta.get("elective_skills", ""))
                # Backward compat: very old docs stored a single flat "skills" field.
                if not essential and not elective:
                    legacy = self._parse_skill_string(meta.get("skills", ""))
                    essential = legacy
                # Enforce split invariant on read as well.
                essential_set = set(essential)
                elective = [s for s in elective if s not in essential_set]
                
                emb = results["embeddings"][0]
                if hasattr(emb, "tolist"):
                    emb = emb.tolist()
                    
                return {
                    "job_description": results["documents"][0],
                    "skills": {
                        "essential": essential,
                        "elective": elective
                    },
                    "required_experience": meta.get("required_experience", 0.0),
                    "embedding": emb
                }
            return None
        except Exception as e:
            logger.error(f"[JDController] Error retrieving JD from ChromaDB: {e}")
            return None

    def list_jds(self, company_id: str = None) -> list:
        # List all JDs for a company from ChromaDB. | Company
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
            seen = set()
            if results and results["ids"]:
                for i in range(len(results["ids"])):
                    chroma_id = results["ids"][i]
                    meta = results["metadatas"][i] or {}
                    # Skip legacy bare-id duplicates when the scoped copy exists.
                    jd_name = self._display_name(chroma_id, meta)
                    dedupe_key = f"{meta.get('company_id', '')}::{jd_name}"
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    essential_list = self._parse_skill_string(meta.get("essential_skills", ""))
                    elective_list = self._parse_skill_string(meta.get("elective_skills", ""))
                    if not essential_list and not elective_list:
                        essential_list = self._parse_skill_string(meta.get("skills", ""))
                    essential_set = set(essential_list)
                    elective_list = [s for s in elective_list if s not in essential_set]
                    
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
        # Delete a JD from ChromaDB by name. | Company
        # Type: Main function
        """Deletes a JD from ChromaDB. Optionally verifies company ownership."""
        try:
            collection = self.vector_db._get_collection(JD_COLLECTION)

            deleted_any = False
            ids_to_try = []
            if company_id:
                ids_to_try.append(self._chroma_id(jd_name, company_id))
            ids_to_try.append(jd_name)

            for chroma_id in ids_to_try:
                try:
                    collection.delete(ids=[chroma_id])
                    deleted_any = True
                except Exception:
                    continue

            # Safety net: remove any legacy bare-id doc belonging to this company.
            if company_id:
                try:
                    legacy = collection.get(ids=[jd_name], include=["metadatas"])
                    if legacy and legacy.get("ids"):
                        for idx, _id in enumerate(legacy["ids"]):
                            meta = (legacy.get("metadatas") or [{}])[idx] or {}
                            if meta.get("company_id") == company_id:
                                try:
                                    collection.delete(ids=[_id])
                                    deleted_any = True
                                except Exception:
                                    pass
                except Exception:
                    pass
            
            logger.info(f"[JDController] Deleted JD from ChromaDB: {jd_name} (scoped={bool(company_id)})")
            return True if deleted_any else True
        except Exception as e:
            logger.error(f"[JDController] Error deleting JD from ChromaDB: {e}")
            return False
