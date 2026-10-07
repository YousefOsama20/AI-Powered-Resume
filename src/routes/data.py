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
from models.sql_models import User, CustomerProfile, JobApplication, PipelineStage, CandidateDocument

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
    """Upload a CV file (PDF/DOCX) and register it as a CandidateDocument. | Target: Customer"""
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
                
        # Update SQL database with the new Document
        existing_docs = db.query(CandidateDocument).filter_by(customer_id=customer_id).count()
        is_primary = 1 if existing_docs == 0 else 0
        
        new_doc = CandidateDocument(
            customer_id=customer_id,
            file_name=file.filename,
            file_path=file_path,
            vector_id=file_id,
            is_primary=is_primary
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        
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
    """Parse uploaded CV, extract sections, chunk text, and index into ChromaDB. | Target: Customer"""
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

    # Document vector ID was already set during upload.

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
async def download_my_cv(
    document_id: str = None, 
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """Download own CV file. Optionally pass document_id, defaults to primary CV. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        if document_id:
            doc = db.query(CandidateDocument).filter_by(id=document_id, customer_id=customer_id).first()
        else:
            doc = db.query(CandidateDocument).filter_by(customer_id=customer_id, is_primary=1).first()
            if not doc:
                doc = db.query(CandidateDocument).filter_by(customer_id=customer_id).first()

        if not doc or not doc.file_path or not os.path.exists(doc.file_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "CV file not found."}
            )
        return FileResponse(path=doc.file_path, filename=doc.file_name)
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
    """Download a candidate CV only if they are at CONSIDERED stage or beyond. | Target: Company"""
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
        if application_record.document_id:
            doc = db.query(CandidateDocument).filter_by(id=application_record.document_id).first()
        else:
            doc = db.query(CandidateDocument).filter_by(customer_id=customer_id, is_primary=1).first()
            if not doc:
                doc = db.query(CandidateDocument).filter_by(customer_id=customer_id).first()
                
        if not doc or not doc.file_path or not os.path.exists(doc.file_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Candidate's CV file not found on the server."}
            )
            
        return FileResponse(path=doc.file_path, filename=doc.file_name)
        
    except Exception as e:
        logger.error(f"Error downloading candidate CV: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )

@data_router.get("/customer/documents")
async def list_my_documents(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """List all uploaded CV documents for the logged-in candidate. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        docs = db.query(CandidateDocument).filter_by(customer_id=customer_id).all()
        results = []
        for doc in docs:
            results.append({
                "id": doc.id,
                "file_name": doc.file_name,
                "is_primary": bool(doc.is_primary),
                "created_at": doc.created_at.isoformat()
            })
        return JSONResponse(content={"documents": results})
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@data_router.delete("/customer/documents/{document_id}")
async def delete_my_document(
    document_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """Delete a CV from disk, ChromaDB, and PostgreSQL. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        doc = db.query(CandidateDocument).filter_by(id=document_id, customer_id=customer_id).first()
        if not doc:
            return JSONResponse(status_code=404, content={"message": "Document not found."})
        
        # Remove file from disk
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            
        # Delete from ChromaDB
        try:
            from controllers.VectorDBController import VectorDBController
            vdb = VectorDBController()
            vdb.delete_by_file(customer_id=customer_id, file_id=doc.vector_id, collection_name="candidates")
        except Exception as vec_e:
            logger.error(f"Could not delete from ChromaDB: {vec_e}")

        db.delete(doc)
        db.commit()
        return JSONResponse(content={"message": "Document deleted successfully."})
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
