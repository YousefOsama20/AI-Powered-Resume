from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging
import mimetypes
import os

import aiofiles

from stores.db.database import get_db
from helpers.config import get_settings, Settings
from controllers.DataController import DataController
from models.sql_models import User, CustomerProfile, CompanyProfile, JobType, JobFunction, customer_job_type, customer_job_function
from routes.deps import get_current_customer, get_current_company

logger = logging.getLogger('uvicorn.error')

AVATAR_MAX_SIZE_MB = 5

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
            "photo_url": "/profile/customer/photo" if getattr(profile, "photo_path", None) else None,
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
            "photo_url": "/profile/company/photo" if getattr(profile, "photo_path", None) else None,
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


def _remove_old_photo(photo_path: Optional[str]) -> None:
    try:
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
    except Exception as e:
        logger.warning(f"Could not remove old profile photo {photo_path}: {e}")


def _photo_response(photo_path: Optional[str]):
    if not photo_path or not os.path.exists(photo_path):
        return JSONResponse(status_code=404, content={"message": "Profile photo not found."})
    media_type, _ = mimetypes.guess_type(photo_path)
    return FileResponse(path=photo_path, media_type=media_type or "application/octet-stream")


async def _save_profile_photo(file: UploadFile, profile_id: str, app_settings: Settings) -> str:
    data_controller = DataController()
    is_valid, signal = data_controller.validate_image_file(file=file)
    if not is_valid:
        raise ValueError(signal)

    file_path = data_controller.generate_unique_avatar_filepath(
        orig_file_name=file.filename or "avatar",
        profile_id=profile_id,
    )
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
            await f.write(chunk)
    # Enforce size limit even when UploadFile.size was unavailable upfront.
    if os.path.getsize(file_path) > AVATAR_MAX_SIZE_MB * 1024 * 1024:
        os.remove(file_path)
        raise ValueError("FILE_SIZE_EXCEEDED")
    return file_path


@profile_router.post("/customer/photo")
async def upload_customer_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
):
    """Upload/replace the candidate profile photo (JPEG/PNG/WebP, max 5MB). | Target: Customer"""
    try:
        profile = current_user.customer_profile
        if not profile:
            return JSONResponse(status_code=404, content={"message": "Customer profile not found."})
        try:
            file_path = await _save_profile_photo(file=file, profile_id=profile.id, app_settings=app_settings)
        except ValueError as ve:
            return JSONResponse(status_code=400, content={"message": str(ve)})
        _remove_old_photo(getattr(profile, "photo_path", None))
        profile.photo_path = file_path
        db.commit()
        return JSONResponse(content={"message": "Profile photo uploaded.", "photo_url": "/profile/customer/photo"})
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading customer photo: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})


@profile_router.get("/customer/photo")
async def get_customer_photo(
    current_user: User = Depends(get_current_customer),
):
    """Download own candidate profile photo. | Target: Customer"""
    profile = current_user.customer_profile
    if not profile:
        return JSONResponse(status_code=404, content={"message": "Customer profile not found."})
    return _photo_response(getattr(profile, "photo_path", None))


@profile_router.delete("/customer/photo")
async def delete_customer_photo(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Remove the candidate profile photo. | Target: Customer"""
    try:
        profile = current_user.customer_profile
        if not profile:
            return JSONResponse(status_code=404, content={"message": "Customer profile not found."})
        _remove_old_photo(getattr(profile, "photo_path", None))
        profile.photo_path = None
        db.commit()
        return JSONResponse(content={"message": "Profile photo removed."})
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting customer photo: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})


@profile_router.post("/company/photo")
async def upload_company_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
):
    """Upload/replace the company profile photo/logo (JPEG/PNG/WebP, max 5MB). | Target: Company"""
    try:
        profile = current_user.company_profile
        if not profile:
            return JSONResponse(status_code=404, content={"message": "Company profile not found."})
        try:
            file_path = await _save_profile_photo(file=file, profile_id=profile.id, app_settings=app_settings)
        except ValueError as ve:
            return JSONResponse(status_code=400, content={"message": str(ve)})
        _remove_old_photo(getattr(profile, "photo_path", None))
        profile.photo_path = file_path
        db.commit()
        return JSONResponse(content={"message": "Profile photo uploaded.", "photo_url": "/profile/company/photo"})
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading company photo: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})


@profile_router.get("/company/photo")
async def get_company_photo(
    current_user: User = Depends(get_current_company),
):
    """Download own company profile photo/logo. | Target: Company"""
    profile = current_user.company_profile
    if not profile:
        return JSONResponse(status_code=404, content={"message": "Company profile not found."})
    return _photo_response(getattr(profile, "photo_path", None))


@profile_router.delete("/company/photo")
async def delete_company_photo(
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """Remove the company profile photo/logo. | Target: Company"""
    try:
        profile = current_user.company_profile
        if not profile:
            return JSONResponse(status_code=404, content={"message": "Company profile not found."})
        _remove_old_photo(getattr(profile, "photo_path", None))
        profile.photo_path = None
        db.commit()
        return JSONResponse(content={"message": "Profile photo removed."})
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting company photo: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
