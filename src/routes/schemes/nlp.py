from pydantic import BaseModel
from typing import Optional, List

class NLPIndexRequest(BaseModel):
    file_id: str
    chunk_size: Optional[int] = 1000
    overlap_size: Optional[int] = 200
    # None = use the canonical CANDIDATE_COLLECTION server-side.
    collection_name: Optional[str] = None

class NLPJDStoreRequest(BaseModel):
    jd_name: str
    job_description: str
    is_public: Optional[int] = 0
    location: Optional[str] = None
    job_type_id: Optional[str] = None
    job_function_id: Optional[str] = None
    required_experience: Optional[float] = None

class NLPJDUpdateRequest(BaseModel):
    jd_name: str
    job_description: str
    is_public: Optional[int] = 0
    location: Optional[str] = None
    job_type_id: Optional[str] = None
    job_function_id: Optional[str] = None

class NLPJDIdUpdateRequest(BaseModel):
    job_description: str
    is_public: Optional[int] = None
    location: Optional[str] = None
    job_type_id: Optional[str] = None
    job_function_id: Optional[str] = None

class NLPMatchRequest(BaseModel):
    job_description: Optional[str] = None
    jd_name: Optional[str] = None
    jd_id: Optional[str] = None
    top_k: Optional[int] = 10

class NLPdeleteRequest(BaseModel):
    file_id: str