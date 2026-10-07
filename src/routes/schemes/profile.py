from pydantic import BaseModel

class CustomerProfileUpdate(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    job_type_ids: Optional[List[str]] = None
    job_function_ids: Optional[List[str]] = None

class company_name(BaseModel):
    company_name: Optional[str] = None
    description: Optional[str] = None