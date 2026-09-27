from pydantic import BaseModel
from typing import Optional


class NLPIndexRequest(BaseModel):
    file_id: str
    chunk_size: Optional[int] = 500
    overlap_size: Optional[int] = 50
    collection_name: Optional[str] = None


class NLPMatchRequest(BaseModel):
    job_description: str
    top_k: Optional[int] = 5
