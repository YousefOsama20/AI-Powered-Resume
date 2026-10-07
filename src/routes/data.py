import os
import aiofiles
import logging
from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from models import ResponseSignal
from .schemes.data import ProcessRequest
from routes.deps import get_current_customer, get_current_company
from stores.db.database import get_db
from models.sql_models import User, CustomerProfile, JobApplication, PipelineStage

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload")
async def upload_data(file: UploadFile,
                      app_settings: Settings = Depends(get_settings),
                      current_user: User = Depends(get_current_customer),
                      db: Session = Depends(get_db)):
    # Type: Main function
    
    # validate the file properties
    data_controller = DataController()

    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": result_signal}
        )

    customer_id = current_user.customer_profile.id

    # We reuse ProjectController's path generation but pass customer_id instead of customer_id
    project_dir_path = ProjectController().get_customer_path(customer_id=customer_id)
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename,
        customer_id=customer_id
    )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
                
        # Update SQL database with the uploaded file path
        current_user.customer_profile.cv_file_path = file_path
        db.commit()
        
    except Exception as e:
        logger.error(f"Error while uploading file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.FILE_UPLOAD_FAILED.value}
        )

    return JSONResponse(
            content={
                "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "file_id": file_id
            }
        )

@data_router.post("/process")
async def process_endpoint(process_request: ProcessRequest,
                           current_user: User = Depends(get_current_customer),
                           db: Session = Depends(get_db)):
    # Type: Main function

    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size

    customer_id = current_user.customer_profile.id
    process_controller = ProcessController(customer_id=customer_id)

    file_content = process_controller.get_file_content(file_id=file_id)

    if not file_content:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.NO_FILES_ERROR.value}
        )

    file_chunks = process_controller.process_file_content(
        file_content=file_content,
        file_id=file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size
    )

    if file_chunks is None or len(file_chunks) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROCESSING_FAILED.value}
        )

    # Save vector DB ID to customer profile
    current_user.customer_profile.cv_vector_id = file_id
    db.commit()

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "total_chunks": len(file_chunks),
            "chunks": [
                {
                    "page_content": chunk.page_content,
                    "metadata": chunk.metadata
                }
                for chunk in file_chunks
            ]
        }
    )

@data_router.get("/download/me")
async def download_my_cv(current_user: User = Depends(get_current_customer)):
    """
    Customer downloads their own uploaded CV.
    """
    try:
        cv_path = current_user.customer_profile.cv_file_path
        if not cv_path or not os.path.exists(cv_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "CV file not found."}
            )
        return FileResponse(path=cv_path, filename=os.path.basename(cv_path))
    except Exception as e:
        logger.error(f"Error downloading own CV: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )

@data_router.get("/download/candidate/{customer_id}")
async def download_candidate_cv(
    customer_id: str,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """
    Company downloads a candidate's CV ONLY if the candidate has accepted their request.
    """
    try:
        company_id = current_user.company_profile.id
        
        # Verify there is a valid ATS stage (CONSIDERED or later)
        application_record = db.query(JobApplication).filter(
            JobApplication.company_id == company_id,
            JobApplication.customer_id == customer_id,
            JobApplication.stage.in_([
                PipelineStage.CONSIDERED, 
                PipelineStage.INTERVIEWING, 
                PipelineStage.OFFER_SENT, 
                PipelineStage.HIRED
            ])
        ).first()
        
        if not application_record:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"message": "You do not have an accepted request from this candidate."}
            )
            
        # Get the CV path
        customer = db.query(CustomerProfile).filter_by(id=customer_id).first()
        if not customer or not customer.cv_file_path or not os.path.exists(customer.cv_file_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Candidate's CV file not found on the server."}
            )
            
        return FileResponse(path=customer.cv_file_path, filename=os.path.basename(customer.cv_file_path))
        
    except Exception as e:
        logger.error(f"Error downloading candidate CV: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )
