from pydantic import BaseModel
from typing import Optional, List

class NLPIndexRequest(BaseModel):
    file_id: str
    chunk_size: Optional[int] = 1000
    overlap_size: Optional[int] = 200
    collection_name: Optional[str] = "candidates"

class NLPJDStoreRequest(BaseModel):
    jd_name: str
    job_description: str
    is_public: Optional[int] = 0
    location: Optional[str] = None
    job_type_id: Optional[str] = None
    job_function_id: Optional[str] = None

class NLPJDUpdateRequest(BaseModel):
    jd_name: str
    job_description: str
    is_public: Optional[int] = 0
    location: Optional[str] = None
    job_type_id: Optional[str] = None
    job_function_id: Optional[str] = None

class NLPMatchRequest(BaseModel):
    job_description: Optional[str] = None
    jd_name: Optional[str] = None
    top_k: Optional[int] = 5

class NLPdeleteRequest(BaseModel):
    file_id: str