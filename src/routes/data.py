import os
import aiofiles
import logging
from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from models import ResponseSignal
from .schemes.data import ProcessRequest
from routes.deps import get_current_customer
from stores.db.database import get_db
from models.sql_models import User

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
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

    # We reuse ProjectController's path generation but pass customer_id instead of project_id
    project_dir_path = ProjectController().get_project_path(project_id=customer_id)
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename,
        project_id=customer_id
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
