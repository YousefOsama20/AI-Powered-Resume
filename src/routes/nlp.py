from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import JSONResponse
import logging
from sqlalchemy.orm import Session

from controllers import ProcessController, EmbeddingController, VectorDBController, MatchController, ExtractionController, ExperienceController, LLMExtractionController, JDController
from models import ResponseSignal
from .schemes.nlp import NLPIndexRequest, NLPMatchRequest, NLPJDStoreRequest, NLPdeleteRequest, NLPJDUpdateRequest
from routes.deps import get_current_customer, get_current_company
from models.sql_models import User, JobDescription, CustomerProfile
from stores.db.database import get_db

logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/nlp",
    tags=["api_v1", "nlp"],
)

@nlp_router.get("/files")
async def list_indexed_files():
    # Type: Main function
    """
    Returns a list of all file_id and project_id combinations stored in the VectorDB.
    """
    try:
        vectordb_controller = VectorDBController()
        files = vectordb_controller.get_all_indexed_files()
        
        return JSONResponse(
            content={
                "message": "Files retrieved successfully.",
                "total": len(files),
                "files": files
            }
        )
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )

@nlp_router.post("/index")
async def index_file(request: NLPIndexRequest, current_user: User = Depends(get_current_customer)):
    # Type: Main function
    """
    Parse a file for a customer, embed its chunks, and store them in the Vector DB.
    Uses LLM for skill extraction if available, falls back to taxonomy.
    """
    try:
        customer_id = current_user.customer_profile.id
        
        # 1. Parse and chunk the file
        process_controller = ProcessController(customer_id=customer_id)
        file_content = process_controller.get_file_content(file_id=request.file_id)
        
        if not file_content:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"signal": ResponseSignal.NO_FILES_ERROR.value}
            )

        chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=request.file_id,
            chunk_size=request.chunk_size,
            overlap_size=request.overlap_size
        )

        if not chunks:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.PROCESSING_FAILED.value}
            )

        # 2. Generate embeddings, extract skills, and extract experience
        embedding_controller = EmbeddingController()
        extraction_controller = ExtractionController()
        experience_controller = ExperienceController()
        llm_extraction_controller = LLMExtractionController()
        
        # Combine all chunk text for a single LLM call (more accurate + saves API calls)
        full_resume_text = "\n\n".join([chunk.page_content for chunk in chunks])
        
        # Try LLM extraction first, fallback to taxonomy
        llm_skills = []
        if llm_extraction_controller.is_available:
            llm_skills = llm_extraction_controller.extract_skills_from_cv(full_resume_text)
            logger.info(f"[Index] LLM extracted {len(llm_skills)} skills from CV")

        texts_to_embed = []
        for chunk in chunks:
            texts_to_embed.append(chunk.page_content)
            
            # Use LLM skills if available, otherwise fallback to taxonomy per-chunk
            if llm_skills:
                # Filter LLM skills to those relevant to this chunk
                chunk_text_lower = chunk.page_content.lower()
                chunk_skills = [s for s in llm_skills if s in chunk_text_lower]
                # If no LLM skills matched this specific chunk, use taxonomy as backup
                if not chunk_skills:
                    chunk_skills = extraction_controller.extract_skills(chunk.page_content)
            else:
                # Fallback: taxonomy-based extraction (old method)
                chunk_skills = extraction_controller.extract_skills(chunk.page_content)
            
            chunk.metadata["skills"] = ",".join(chunk_skills)

            # Extract years of experience from Experience-section chunks
            if chunk.metadata.get("section") == "Experience":
                exp_years = experience_controller.extract_candidate_experience(chunk.page_content)
                chunk.metadata["experience_years"] = exp_years
            else:
                chunk.metadata["experience_years"] = 0.0
            
        embeddings = embedding_controller.embed_texts(texts_to_embed)

        if not embeddings or len(embeddings) != len(chunks):
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.EMBEDDING_FAILED.value}
            )

        # 3. Store in VectorDB
        vectordb_controller = VectorDBController()
        success = vectordb_controller.index_chunks(
            chunks=chunks,
            embeddings=embeddings,
            collection_name=request.collection_name
        )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.VECTORDB_INDEX_FAILED.value}
            )

        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_INDEX_SUCCESS.value,
                "customer_id": customer_id,
                "file_id": request.file_id,
                "indexed_chunks": len(chunks),
                "collection": request.collection_name or vectordb_controller.default_collection,
                "total_in_collection": vectordb_controller.get_collection_count(request.collection_name)
            }
        )

    except Exception as e:
        logger.error(f"Error in indexing endpoint: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_INDEX_FAILED.value}
        )


@nlp_router.get("/jd")
async def list_job_descriptions(current_user: User = Depends(get_current_company)):
    """List all Job Descriptions owned by the logged-in company. | Target: Company"""
    # Type: Main function
    """
    Returns a list of all Job Description names owned by the logged-in company.
    """
    try:
        company_id = current_user.company_profile.id
        jd_controller = JDController()
        jds = jd_controller.list_jds(company_id=company_id)
        
        return JSONResponse(
            content={
                "message": "Job descriptions retrieved successfully.",
                "total": len(jds),
                "jds": jds
            }
        )
    except Exception as e:
        logger.error(f"Error listing JDs: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )


@nlp_router.post("/jd")
async def store_job_description(request: NLPJDStoreRequest, current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """Create a new Job Description, extract skills via LLM, and embed into ChromaDB. | Target: Company"""
    # Type: Main function
    """
    Extracts skills, embeddings, and required experience from a Job Description,
    and stores them in both JSON (metadata) and ChromaDB (chunks + vectors).
    Also persists JD ownership to the SQL database.
    """
    try:
        jd_name = request.jd_name.strip()
        job_description = request.job_description.strip()
        company_id = current_user.company_profile.id
        
        if not jd_name or not job_description:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "jd_name and job_description are required."}
            )

        # 1. Extract skills via LLM (classified) or taxonomy (fallback)
        llm_extraction = LLMExtractionController()
        extraction = ExtractionController()
        
        if llm_extraction.is_available:
            skills = llm_extraction.extract_skills_from_jd(job_description)
        else:
            # Taxonomy fallback: all skills go to "essential"
            flat_skills = extraction.extract_skills(job_description)
            skills = {"essential": flat_skills, "elective": []}
            
        # 2. Extract required experience
        experience_controller = ExperienceController()
        required_exp = experience_controller.extract_required_experience(job_description)
        
        # 3. Create embedding for the full JD
        embedding_controller = EmbeddingController()
        embedding = embedding_controller.embed_text(job_description)
        
        if not embedding:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to create JD embedding."}
            )

        # 4. Store in ChromaDB
        jd_controller = JDController()
        success = jd_controller.store_jd(
            jd_name=jd_name,
            company_id=company_id,
            job_description=job_description,
            skills=skills,
            required_exp=required_exp,
            embedding=embedding
        )
        
        if success:
            # 5. Store ownership in SQL Database
            existing_jd = db.query(JobDescription).filter_by(company_id=company_id, jd_name=jd_name).first()
            if not existing_jd:
                new_jd = JobDescription(
                    company_id=company_id, 
                    jd_name=jd_name,
                    is_public=request.is_public,
                    location=request.location,
                    job_type_id=request.job_type_id,
                    job_function_id=request.job_function_id
                )
                db.add(new_jd)
                db.commit()

            return JSONResponse(
                content={
                    "message": "Job description stored successfully.",
                    "jd_name": jd_name,
                    "company_id": company_id,
                    "essential_skills": skills["essential"],
                    "elective_skills": skills["elective"],
                    "essential_count": len(skills["essential"]),
                    "elective_count": len(skills["elective"]),
                    "total_skills": len(skills["essential"]) + len(skills["elective"]),
                    "required_experience": required_exp
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to store job description to database."}
            )
            
    except Exception as e:
        logger.error(f"Error storing JD: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )


@nlp_router.put("/jd")
async def update_job_description(request: NLPJDUpdateRequest, current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """Update an existing JD, re-extract skills and re-embed. | Target: Company"""
    # Type: Main function
    """
    Updates an existing Job Description owned by the logged-in company.
    Re-extracts skills, embeddings, and required experience based on the new text.
    """
    try:
        jd_name = request.jd_name.strip()
        job_description = request.job_description.strip()
        company_id = current_user.company_profile.id
        
        jd_controller = JDController()
        
        # Check ownership in SQL database first
        existing_jd = db.query(JobDescription).filter_by(company_id=company_id, jd_name=jd_name).first()
        if not existing_jd:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Job description '{jd_name}' not found or you don't have permission."}
            )

        if not job_description:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "job_description is required."}
            )

        # 1. Re-extract skills via LLM (classified) or taxonomy (fallback)
        llm_extraction = LLMExtractionController()
        extraction = ExtractionController()
        
        if llm_extraction.is_available:
            skills = llm_extraction.extract_skills_from_jd(job_description)
        else:
            flat_skills = extraction.extract_skills(job_description)
            skills = {"essential": flat_skills, "elective": []}
            
        # 2. Re-extract required experience
        experience_controller = ExperienceController()
        required_exp = experience_controller.extract_required_experience(job_description)
        
        # 3. Re-create embedding
        embedding_controller = EmbeddingController()
        embedding = embedding_controller.embed_text(job_description)
        
        if not embedding:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to create JD embedding."}
            )

        # 4. Store natively in ChromaDB (upsert automatically overwrites)
        success = jd_controller.store_jd(
            jd_name=jd_name,
            company_id=company_id,
            job_description=job_description,
            skills=skills,
            required_exp=required_exp,
            embedding=embedding
        )
        
        if success:
            return JSONResponse(
                content={
                    "message": "Job description updated successfully.",
                    "jd_name": jd_name,
                    "company_id": company_id,
                    "essential_skills": skills["essential"],
                    "elective_skills": skills["elective"],
                    "essential_count": len(skills["essential"]),
                    "elective_count": len(skills["elective"]),
                    "total_skills": len(skills["essential"]) + len(skills["elective"]),
                    "required_experience": required_exp
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to update job description in database."}
            )
            
    except Exception as e:
        logger.error(f"Error updating JD: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )


@nlp_router.delete("/jd/{jd_name}")
async def delete_job_description(jd_name: str, current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """Delete a JD from both PostgreSQL and ChromaDB. | Target: Company"""
    # Type: Main function
    """
    Deletes a Job Description owned by the logged-in company from both SQL and ChromaDB.
    """
    try:
        company_id = current_user.company_profile.id
        
        # Check ownership in SQL
        existing_jd = db.query(JobDescription).filter_by(company_id=company_id, jd_name=jd_name).first()
        if not existing_jd:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Job description '{jd_name}' not found or you don't have permission."}
            )
            
        # Delete from SQL
        db.delete(existing_jd)
        db.commit()
        
        # Delete from ChromaDB
        jd_controller = JDController()
        jd_controller.delete_jd(jd_name, company_id=company_id)
        
        return JSONResponse(
            content={
                "message": "Job description deleted successfully.",
                "jd_name": jd_name
            }
        )
    except Exception as e:
        logger.error(f"Error deleting JD: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )


@nlp_router.post("/match")
async def match_resumes(request: NLPMatchRequest, current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """Run hybrid AI matching (Semantic + Keywords + Experience) against candidate pool. | Target: Company"""
    # Type: Main function
    """
    Match Job Description against all candidates in the global candidate pool.
    Can accept a raw job_description string OR a pre-stored jd_name.
    Enriches results with candidate profile data from PostgreSQL.
    """
    try:
        company_id = current_user.company_profile.id

        if not request.job_description and not request.jd_name:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.EMPTY_JOB_DESCRIPTION.value}
            )

        # If using a stored JD, verify ownership
        if request.jd_name:
            owned_jd = db.query(JobDescription).filter_by(
                company_id=company_id, jd_name=request.jd_name
            ).first()
            if not owned_jd:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"message": f"Job description '{request.jd_name}' not found or you don't have permission."}
                )

        match_controller = MatchController()
        results, jd_skills = match_controller.match_candidates(
            customer_id=None,  # Global search
            job_description=request.job_description,
            jd_name=request.jd_name,
            top_k=request.top_k
        )

        # Enrich results with CustomerProfile data from PostgreSQL
        enriched_results = []
        for result in results:
            cust_id = result.get("customer_id", "")
            profile = db.query(CustomerProfile).filter_by(id=cust_id).first() if cust_id else None
            
            result["candidate_name"] = profile.name if profile else "Unknown"
            result["candidate_location"] = profile.location if profile else None
            result["has_accepted_request"] = False  # Will be used in Phase 7
            enriched_results.append(result)

        return JSONResponse(
            content={
                "signal": ResponseSignal.MATCH_SUCCESS.value,
                "company_id": company_id,
                "jd_skills": jd_skills,
                "total_matches": len(enriched_results),
                "results": enriched_results
            }
        )

    except Exception as e:
        logger.error(f"Error in match endpoint: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.MATCH_FAILED.value}
        )


@nlp_router.delete("/delete/file")
async def delete_file_index(request: NLPdeleteRequest, current_user: User = Depends(get_current_customer)):
    # Type: Main function
    """
    Delete indexed chunks for a specific file belonging to the logged-in customer.
    """
    try:
        customer_id = current_user.customer_profile.id
        vectordb_controller = VectorDBController()
        success = vectordb_controller.delete_by_file(
            customer_id=customer_id,
            file_id=request.file_id
        )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
            )

        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_DELETE_SUCCESS.value,
                "customer_id": customer_id,
                "file_id": request.file_id
            }
        )
    except Exception as e:
        logger.error(f"Error deleting file from VectorDB: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
        )

@nlp_router.delete("/delete/customer")
async def delete_customer_index(current_user: User = Depends(get_current_customer)):
    # Type: Main function
    """
    Delete all indexed chunks for the logged-in customer.
    """
    try:
        customer_id = current_user.customer_profile.id
        vectordb_controller = VectorDBController()
        success = vectordb_controller.delete_by_customer(customer_id=customer_id)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
            )

        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_DELETE_SUCCESS.value,
                "customer_id": customer_id
            }
        )
    except Exception as e:
        logger.error(f"Error deleting customer data from VectorDB: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
        )

@nlp_router.get("/recommend-jobs")
async def recommend_jobs(
    document_id: str = None,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
):
    """Get recommended jobs based on candidate CV. | Target: Customer"""
    try:
        if not document_id:
            from models.sql_models import CandidateDocument
            doc = db.query(CandidateDocument).filter_by(customer_id=current_user.customer_profile.id, is_primary=1).first()
            if not doc:
                doc = db.query(CandidateDocument).filter_by(customer_id=current_user.customer_profile.id).first()
            if doc:
                document_id = doc.id
            else:
                return JSONResponse(status_code=404, content={"message": "No CV found to match against."})
                
        match_controller = MatchController()
        recommended = match_controller.recommend_jobs(db=db, document_id=document_id, top_k=5)
        return JSONResponse(content={"recommended_jobs": recommended})
    except Exception as e:
        import traceback; logger.error(f"Error recommending jobs: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
