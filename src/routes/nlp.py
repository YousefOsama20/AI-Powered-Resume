from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import JSONResponse
import logging
from sqlalchemy.orm import Session

from controllers import ProcessController, EmbeddingController, VectorDBController, MatchController, ExtractionController, ExperienceController, LLMExtractionController, JDController
from models import ResponseSignal
from .schemes.nlp import NLPIndexRequest, NLPMatchRequest, NLPJDStoreRequest, NLPdeleteRequest, NLPJDUpdateRequest, NLPJDIdUpdateRequest
from controllers.VectorDBController import CANDIDATE_COLLECTION
from routes.deps import get_current_customer, get_current_company
from models.sql_models import User, JobDescription, CustomerProfile
from stores.db.database import get_db

logger = logging.getLogger('uvicorn.error')


def _normalize_classified_skills(skills) -> dict:
    """Canonicalize + dedupe + ensure elective never duplicates essential."""
    try:
        from controllers.SkillNormalizer import normalize_classified as _canon
        return _canon(skills)
    except Exception:
        def _clean(items):
            seen = set()
            out = []
            for s in items or []:
                if isinstance(s, str):
                    v = s.strip().lower()
                    if v and v not in seen:
                        seen.add(v)
                        out.append(v)
            return out
        skills = skills or {}
        essential = _clean(skills.get("essential", []))
        elective = _clean(skills.get("elective", []))
        essential_set = set(essential)
        elective = [s for s in elective if s not in essential_set]
        return {"essential": essential, "elective": elective}


def _extract_jd_skills(job_description: str) -> dict:
    """LLM-first extraction with heuristic taxonomy fallback.

    Guarantees an essential/elective split attempt even when the LLM is
    down, misconfigured, or returns an empty result (previously stored as
    empty/empty, which hid the Required Skills block for customers).
    """
    llm_extraction = LLMExtractionController()
    extraction = ExtractionController()
    skills = {"essential": [], "elective": []}
    if llm_extraction.is_available:
        try:
            result = llm_extraction.extract_skills_from_jd(job_description)
            if isinstance(result, dict):
                skills = _normalize_classified_skills(result)
        except Exception as e:
            logger.warning(f"[JD skills] LLM extraction failed, using fallback: {e}")
            skills = {"essential": [], "elective": []}
    total = len(skills.get("essential", [])) + len(skills.get("elective", []))
    if total == 0:
        try:
            skills = _normalize_classified_skills(
                extraction.extract_classified_skills(job_description)
            )
        except Exception as e:
            logger.warning(f"[JD skills] Heuristic fallback failed: {e}")
    if total == 0 and (not skills.get("essential") and not skills.get("elective")):
        logger.warning("[JD skills] No skills extracted by LLM nor heuristic fallback.")
    else:
        logger.info(
            f"[JD skills] final: {len(skills['essential'])} essential, "
            f"{len(skills['elective'])} elective"
        )
    return skills

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
        try:
            from controllers.SkillNormalizer import normalize_skill_list as _canon_list
            llm_skills = _canon_list(llm_skills)
        except Exception:
            pass

        texts_to_embed = []
        for chunk in chunks:
            texts_to_embed.append(chunk.page_content)

            # Use LLM skills if available, otherwise fallback to taxonomy per-chunk.
            # Canonicalize before substring check so "rest api" matches "REST APIs".
            if llm_skills:
                import re as _re
                norm_chunk = _re.sub(r"[-_]", " ", chunk.page_content.lower())
                norm_chunk = _re.sub(r"\s+", " ", norm_chunk)
                chunk_skills = [s for s in llm_skills if s and s in norm_chunk]
                # Union with taxonomy skills for this chunk (never lose either side)
                try:
                    tax_skills = extraction_controller.extract_skills(chunk.page_content)
                    for t in tax_skills:
                        if t not in chunk_skills:
                            chunk_skills.append(t)
                except Exception:
                    pass
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

        # Safety net: every global LLM skill must live in at least one chunk,
        # otherwise inferred skills (e.g. "problem solving") vanish from matching.
        if llm_skills and chunks:
            stored = set()
            for c in chunks:
                for s in (c.metadata.get("skills") or "").split(","):
                    s = s.strip()
                    if s:
                        stored.add(s)
            missing_global = [s for s in llm_skills if s not in stored]
            if missing_global:
                first = chunks[0].metadata.get("skills") or ""
                extra = ",".join(missing_global)
                chunks[0].metadata["skills"] = f"{first},{extra}" if first else extra
                logger.info(f"[Index] Restored {len(missing_global)} global LLM skills to first chunk")
            
        embeddings = embedding_controller.embed_texts(texts_to_embed)

        if not embeddings or len(embeddings) != len(chunks):
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.EMBEDDING_FAILED.value}
            )

        # 3. Store in VectorDB (default to the canonical candidates collection)
        vectordb_controller = VectorDBController()
        target_collection = request.collection_name or CANDIDATE_COLLECTION
        success = vectordb_controller.index_chunks(
            chunks=chunks,
            embeddings=embeddings,
            collection_name=target_collection
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
                "collection": target_collection,
                "total_in_collection": vectordb_controller.get_collection_count(target_collection)
            }
        )

    except Exception as e:
        logger.error(f"Error in indexing endpoint: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_INDEX_FAILED.value}
        )


@nlp_router.get("/jd")
async def list_job_descriptions(current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """List all Job Descriptions owned by the logged-in company. | Target: Company"""
    try:
        company_id = current_user.company_profile.id
        jds = db.query(JobDescription).filter_by(company_id=company_id).all()
        
        results = []
        for jd in jds:
            results.append({
                "jd_id": jd.id,
                "jd_name": jd.jd_name,
                "is_public": jd.is_public,
                "location": jd.location,
                "created_at": jd.created_at.isoformat()
            })
            
        return JSONResponse(
            content={
                "message": "Job descriptions retrieved successfully.",
                "total": len(results),
                "jds": results
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

        # Fail fast on duplicate titles: previously a repeat jd_name silently
        # upserted the Chroma doc and skipped the SQL insert, returning 200
        # while the JD list did not grow — looking like "can't post another JD".
        duplicate = db.query(JobDescription).filter_by(company_id=company_id, jd_name=jd_name).first()
        if duplicate:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"message": f"A job posting named '{jd_name}' already exists. Use a different title or edit the existing one."}
            )

        # 1. Extract skills via LLM (classified) with heuristic fallback
        skills = _extract_jd_skills(job_description)
            
        # 2. Required experience: prefer the explicit form value when supplied,
        # otherwise auto-extract from the JD text.
        if request.required_experience is not None:
            try:
                required_exp = max(0.0, float(request.required_experience))
            except (TypeError, ValueError):
                experience_controller = ExperienceController()
                required_exp = experience_controller.extract_required_experience(job_description)
        else:
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
            try:
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
                db.refresh(new_jd)
                jd_id = new_jd.id
            except Exception as e:
                db.rollback()
                logger.error(f"Error persisting JD ownership (company={company_id}, jd_name={jd_name}): {e}")
                # Roll back the Chroma write to avoid SQL/Chroma drift.
                try:
                    jd_controller.delete_jd(jd_name, company_id=company_id)
                except Exception:
                    pass
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"message": "Failed to save job posting. Please check Job Type/Function and try again."}
                )

            return JSONResponse(
                content={
                    "message": "Job description stored successfully.",
                    "jd_id": jd_id,
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
        try:
            db.rollback()
        except Exception:
            pass
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

        # 1. Re-extract skills via LLM (classified) with heuristic fallback
        skills = _extract_jd_skills(job_description)
            
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


@nlp_router.put("/jd/{jd_id}")
async def update_job_description_by_id(jd_id: str, request: NLPJDIdUpdateRequest, current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """Update an existing JD by SQL id, re-extract skills and re-embed. | Target: Company"""
    try:
        company_id = current_user.company_profile.id

        existing_jd = db.query(JobDescription).filter_by(id=jd_id, company_id=company_id).first()
        if not existing_jd:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Job description '{jd_id}' not found or you don't have permission."}
            )

        job_description = (request.job_description or "").strip()
        if not job_description:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "job_description is required."}
            )

        jd_name = existing_jd.jd_name

        # 1. Re-extract skills via LLM (classified) or taxonomy (fallback)
        # 1. Re-extract skills via LLM (classified) with heuristic fallback
        skills = _extract_jd_skills(job_description)

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
        jd_controller = JDController()
        success = jd_controller.store_jd(
            jd_name=jd_name,
            company_id=company_id,
            job_description=job_description,
            skills=skills,
            required_exp=required_exp,
            embedding=embedding
        )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to update job description in database."}
            )

        # 5. Update SQL metadata if provided
        if request.is_public is not None:
            existing_jd.is_public = request.is_public
        if request.location is not None:
            existing_jd.location = request.location
        if request.job_type_id is not None:
            existing_jd.job_type_id = request.job_type_id
        if request.job_function_id is not None:
            existing_jd.job_function_id = request.job_function_id
        db.commit()

        return JSONResponse(
            content={
                "message": "Job description updated successfully.",
                "jd_id": existing_jd.id,
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

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating JD by id: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )


@nlp_router.delete("/jd/{jd_identifier}")
async def delete_job_description(jd_identifier: str, current_user: User = Depends(get_current_company), db: Session = Depends(get_db)):
    """Delete a JD by SQL id (or legacy jd_name) from both PostgreSQL and ChromaDB. | Target: Company"""
    # Type: Main function
    """
    Deletes a Job Description owned by the logged-in company from both SQL and ChromaDB.
    Accepts either the SQL `jd_id` or the legacy `jd_name` as path parameter.
    """
    try:
        company_id = current_user.company_profile.id

        # Check ownership in SQL: try id first, then fall back to jd_name
        existing_jd = db.query(JobDescription).filter_by(id=jd_identifier, company_id=company_id).first()
        if not existing_jd:
            existing_jd = db.query(JobDescription).filter_by(company_id=company_id, jd_name=jd_identifier).first()
        if not existing_jd:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Job description '{jd_identifier}' not found or you don't have permission."}
            )

        jd_name = existing_jd.jd_name
        jd_id = existing_jd.id

        # Delete from SQL
        db.delete(existing_jd)
        db.commit()

        # Delete from ChromaDB
        jd_controller = JDController()
        jd_controller.delete_jd(jd_name, company_id=company_id)

        return JSONResponse(
            content={
                "message": "Job description deleted successfully.",
                "jd_id": jd_id,
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

        if not request.job_description and not request.jd_name and not request.jd_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.EMPTY_JOB_DESCRIPTION.value}
            )

        # If using a stored JD, verify ownership
        owned_jd = None
        if request.jd_id:
            owned_jd = db.query(JobDescription).filter_by(company_id=company_id, id=request.jd_id).first()
            if owned_jd:
                request.jd_name = owned_jd.jd_name
        elif request.jd_name:
            owned_jd = db.query(JobDescription).filter_by(company_id=company_id, jd_name=request.jd_name).first()
            
        if (request.jd_name or request.jd_id) and not owned_jd:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Job description not found or you don't have permission."}
            )

        match_controller = MatchController()
        try:
            requested_top_k = int(request.top_k or 10)
        except (ValueError, TypeError):
            requested_top_k = 10
        requested_top_k = max(1, min(requested_top_k, 50))
        results, jd_skills = match_controller.match_candidates(
            db=db,
            customer_id=None,  # Global search across ALL candidates
            job_description=request.job_description,
            jd_name=request.jd_name,
            top_k=requested_top_k,
            company_id=company_id
        )

        # Enrich results with CustomerProfile + Document data from PostgreSQL.
        # One row per customer (best CV) is returned, sorted by match_score.
        enriched_results = []
        orphan_skipped = 0
        from models.sql_models import JobApplication, CandidateDocument
        for result in results:
            cust_id = result.get("customer_id", "")
            profile = db.query(CustomerProfile).filter_by(id=cust_id).first() if cust_id else None
            
            if not profile:
                orphan_skipped += 1
                continue # Skip orphan vectors from deleted databases

            # Attach CV file info for the matched file (best file per customer).
            file_id = result.get("file_id") or result.get("candidate_id", "")
            doc = None
            if file_id:
                doc = db.query(CandidateDocument).filter_by(customer_id=cust_id, vector_id=file_id).first()
            if doc is None:
                doc = db.query(CandidateDocument).filter_by(customer_id=cust_id, is_primary=1).first()
            if doc is None:
                doc = db.query(CandidateDocument).filter_by(customer_id=cust_id).first()
                
            # Check if already applied or contacted
            already_in_pipeline = False
            if request.jd_id and cust_id:
                app = db.query(JobApplication).filter_by(jd_id=request.jd_id, customer_id=cust_id).first()
                if app:
                    already_in_pipeline = True
            
            result["candidate_name"] = profile.name
            result["candidate_location"] = profile.location
            result["candidate_photo_url"] = f"/ats/candidates/{profile.id}/photo" if getattr(profile, "photo_path", None) else None
            result["file_id"] = file_id
            result["file_name"] = doc.file_name if doc else file_id
            result["document_id"] = doc.id if doc else None
            result["has_accepted_request"] = already_in_pipeline
            enriched_results.append(result)

        if orphan_skipped:
            logger.warning(f"[Match] Skipped {orphan_skipped} orphan vectors without CustomerProfile (company={company_id})")
        logger.info(f"[Match] company={company_id} jd_name={request.jd_name} raw={len(results)} enriched={len(enriched_results)} top_k={requested_top_k}")

        return JSONResponse(
            content={
                "signal": ResponseSignal.MATCH_SUCCESS.value,
                "company_id": company_id,
                "jd_skills": jd_skills,
                "total_matches": len(enriched_results),
                "orphan_skipped": orphan_skipped,
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
    top_k: int = 10,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """Get recommended jobs based on candidate CV. | Target: Customer"""
    try:
        try:
            top_k = max(1, min(int(top_k or 10), 50))
        except (ValueError, TypeError):
            top_k = 10
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
        recommended = match_controller.recommend_jobs(db=db, document_id=document_id, top_k=top_k)
        return JSONResponse(content={"recommended_jobs": recommended})
    except Exception as e:
        import traceback; logger.error(f"Error recommending jobs: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@nlp_router.get("/debug-match")
async def debug_skill_match(
    document_id: str = None,
    jd_id: str = None,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Debug why a CV scores X% on a JD: raw vs canonical skills + matched/missing.

    | Target: Customer (own CV only)
    """
    try:
        from models.sql_models import CandidateDocument
        if not document_id:
            doc = db.query(CandidateDocument).filter_by(
                customer_id=current_user.customer_profile.id, is_primary=1
            ).first()
            if not doc:
                doc = db.query(CandidateDocument).filter_by(
                    customer_id=current_user.customer_profile.id
                ).first()
            if not doc:
                return JSONResponse(status_code=404, content={"message": "No CV found."})
            document_id = doc.id
        else:
            doc = db.query(CandidateDocument).filter_by(
                id=document_id, customer_id=current_user.customer_profile.id
            ).first()
            if not doc:
                return JSONResponse(status_code=404, content={"message": "Document not found."})
        if not jd_id:
            return JSONResponse(status_code=400, content={"message": "jd_id is required."})
        jd_sql = db.query(JobDescription).filter_by(id=jd_id).first()
        if not jd_sql:
            return JSONResponse(status_code=404, content={"message": "JD not found."})

        vectordb_controller = VectorDBController()
        collection = vectordb_controller._get_collection(CANDIDATE_COLLECTION)
        cdata = collection.get(where={"file_id": doc.vector_id}, include=["metadatas"])

        raw_skills: list = []
        for meta in (cdata.get("metadatas") or []):
            for s in (meta.get("skills") or "").split(","):
                s = s.strip()
                if s:
                    raw_skills.append(s)

        from controllers import JDController as _JDC
        jd_data = _JDC().get_jd(jd_sql.jd_name, company_id=jd_sql.company_id) or {}
        jd_skills = jd_data.get("skills", {}) or {}
        jd_essential_raw = list(jd_skills.get("essential", []) or [])
        jd_elective_raw = list(jd_skills.get("elective", []) or [])

        from controllers.SkillNormalizer import (
            normalize_skill_list as _canon_list,
            match_skills as _match_skills,
            score_from_matches as _score,
        )
        cand_canon = _canon_list(raw_skills)
        ess_canon = _canon_list(jd_essential_raw)
        ele_canon = _canon_list(jd_elective_raw)
        m_ess, x_ess, map_ess = _match_skills(set(cand_canon), ess_canon)
        m_ele, x_ele, map_ele = _match_skills(set(cand_canon), ele_canon)
        kw, es, els = _score(m_ess, len(ess_canon), m_ele, len(ele_canon))

        return JSONResponse(content={
            "document_id": document_id,
            "jd_id": jd_id,
            "jd_name": jd_sql.jd_name,
            "candidate_skills_raw": sorted(set(raw_skills)),
            "candidate_skills_canonical": sorted(set(cand_canon)),
            "jd_essential_raw": jd_essential_raw,
            "jd_elective_raw": jd_elective_raw,
            "jd_essential_canonical": sorted(set(ess_canon)),
            "jd_elective_canonical": sorted(set(ele_canon)),
            "matched_essential": sorted(m_ess),
            "missing_essential": sorted(x_ess),
            "matched_elective": sorted(m_ele),
            "missing_elective": sorted(x_ele),
            "match_map": {**map_ess, **map_ele},
            "scores": {
                "keyword_score": round(kw * 100, 2),
                "essential_score": round(es * 100, 2),
                "elective_score": round(els * 100, 2),
            },
        })
    except Exception as e:
        import traceback; logger.error(f"Error in debug-match: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
