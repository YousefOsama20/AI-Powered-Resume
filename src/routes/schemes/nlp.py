from pydantic import BaseModel
from typing import Optional


class NLPIndexRequest(BaseModel):
    file_id: str
    chunk_size: Optional[int] = 500
    overlap_size: Optional[int] = 50
    collection_name: Optional[str] = None


class NLPJDStoreRequest(BaseModel):
    jd_name: str
    job_description: str


class NLPJDUpdateRequest(BaseModel):
    jd_name: str
    job_description: str


class NLPMatchRequest(BaseModel):
    job_description: Optional[str] = None
    jd_name: Optional[str] = None
    top_k: Optional[int] = 5

class NLPdeleteRequest(BaseModel):
    file_id: str