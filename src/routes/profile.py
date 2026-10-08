from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from stores.db.database import get_db
from models.sql_models import User, CustomerProfile, CompanyProfile, JobType, JobFunction, customer_job_type, customer_job_function
from routes.deps import get_current_customer, get_current_company

logger = logging.getLogger('uvicorn.error')

profile_router = APIRouter(
    prefix="/profile",
    tags=["api_v1", "profile"],
)

class CustomerProfileUpdate(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    job_type_ids: Optional[List[str]] = None
    job_function_ids: Optional[List[str]] = None

class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None

@profile_router.get("/customer")
async def get_customer_profile(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """Fetch current candidate personal info. | Target: Customer"""
    try:
        profile = current_user.customer_profile
        if not profile:
            return JSONResponse(status_code=404, content={"message": "Customer profile not found."})
        return JSONResponse(content={
            "email": current_user.email,
            "name": profile.name,
            "phone": profile.phone,
            "location": profile.location,
            "job_types": [{"id": jt.id, "name": jt.name} for jt in profile.job_types],
            "job_functions": [{"id": jf.id, "name": jf.name} for jf in profile.job_functions],
        })
    except Exception as e:
        logger.error(f"Error fetching customer profile: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@profile_router.get("/company")
async def get_company_profile(
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    """Fetch current company profile info. | Target: Company"""
    try:
        profile = current_user.company_profile
        if not profile:
            return JSONResponse(status_code=404, content={"message": "Company profile not found."})
        return JSONResponse(content={
            "email": current_user.email,
            "company_name": profile.company_name,
            "description": profile.description,
            "website": profile.website,
            "industry": profile.industry,
            "location": profile.location,
        })
    except Exception as e:
        logger.error(f"Error fetching company profile: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@profile_router.put("/customer")
async def update_customer_profile(
    payload: CustomerProfileUpdate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """Update candidate profile (phone, location, job types, job functions). | Target: Customer"""
    try:
        profile = current_user.customer_profile
        
        if payload.phone is not None:
            profile.phone = payload.phone
        if payload.location is not None:
            profile.location = payload.location
            
        # Update Many-to-Many relationships
        if payload.job_type_ids is not None:
            profile.job_types.clear()
            for jt_id in payload.job_type_ids:
                jt = db.query(JobType).filter_by(id=jt_id).first()
                if jt:
                    profile.job_types.append(jt)
                    
        if payload.job_function_ids is not None:
            profile.job_functions.clear()
            for jf_id in payload.job_function_ids:
                jf = db.query(JobFunction).filter_by(id=jf_id).first()
                if jf:
                    profile.job_functions.append(jf)

        db.commit()
        return JSONResponse(content={"message": "Profile updated successfully."})
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating customer profile: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@profile_router.put("/company")
async def update_company_profile(
    payload: CompanyProfileUpdate,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    """Update company profile (name, description, website, industry, location). | Target: Company"""
    try:
        profile = current_user.company_profile
        
        if payload.company_name is not None:
            profile.company_name = payload.company_name
        if payload.description is not None:
            profile.description = payload.description
        if payload.website is not None:
            profile.website = payload.website
        if payload.industry is not None:
            profile.industry = payload.industry
        if payload.location is not None:
            profile.location = payload.location

        db.commit()
        return JSONResponse(content={"message": "Profile updated successfully."})
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company profile: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@profile_router.get("/taxonomy")
async def get_taxonomy(db: Session = Depends(get_db)):
    """Fetch all available Job Types and Job Functions for dropdown menus. | Target: Both"""
    try:
        job_types = [{"id": jt.id, "name": jt.name} for jt in db.query(JobType).all()]
        job_functions = [{"id": jf.id, "name": jf.name} for jf in db.query(JobFunction).all()]
        return JSONResponse(content={"job_types": job_types, "job_functions": job_functions})
    except Exception as e:
        logger.error(f"Error fetching taxonomy: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
