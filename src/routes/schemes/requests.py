from pydantic import BaseModel
from typing import Optional
from models.sql_models import PipelineStage

class CreateRequest(BaseModel):
    customer_id: str
    jd_id: str

class UpdateRequestStatus(BaseModel):
    status: PipelineStage
    
class MoveCandidate(BaseModel):
    stage: PipelineStage
