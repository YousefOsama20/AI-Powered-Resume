from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
import json
import logging
import mimetypes
import os

from stores.db.database import get_db
from models.sql_models import (
    User, JobApplication, JobDescription, PipelineStage, CustomerProfile,
    CandidateDocument, ApplyAdviceCache, CompanyProfile,
)
from routes.deps import get_current_company, get_current_customer
from .schemes.requests import CreateRequest, UpdateRequestStatus, MoveCandidate

logger = logging.getLogger('uvicorn.error')

ats_router = APIRouter(
    prefix="/ats",
    tags=["ATS Pipeline"]
)

# ---------------------------------------------------------
# CANDIDATE ACTIONS
# ---------------------------------------------------------

@ats_router.get("/jobs/public")
async def list_public_jobs(db: Session = Depends(get_db)):
    """Browse all public job descriptions to apply. | Target: Customer (or unauthenticated)"""
    try:
        jds = db.query(JobDescription).filter_by(is_public=1).all()
        results = []
        for jd in jds:
            results.append({
                "jd_id": jd.id,
                "jd_name": jd.jd_name,
                "company_name": jd.company.company_name,
                "created_at": jd.created_at.isoformat()
            })
        return JSONResponse(content={"jobs": results})
    except Exception as e:
        logger.error(f"Error listing public jobs: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.get("/jobs/public/{jd_id}")
async def get_public_job_detail(jd_id: str, request: Request, db: Session = Depends(get_db)):
    """Fetch full public JD details: SQL company info + ChromaDB text/skills/experience. | Target: Customer"""
    try:
        jd = db.query(JobDescription).filter_by(id=jd_id, is_public=1).first()
        if not jd:
            return JSONResponse(status_code=404, content={"message": "Job not found."})

        from controllers import JDController
        jd_controller = JDController()
        jd_data = jd_controller.get_jd(jd.jd_name, company_id=jd.company_id)
        if not jd_data:
            return JSONResponse(status_code=404, content={"message": "Job details not found in vector store."})

        skills = jd_data.get("skills", {}) or {}
        essential = list(skills.get("essential", []) or [])
        elective = list(skills.get("elective", []) or [])
        # Read-repair: JDs stored while the LLM was down (or with a legacy
        # flat schema) have empty metadata, which hides the Required Skills
        # block on the customer detail page. Re-derive the split on the fly
        # so customers always see Essential vs Nice-to-have.
        skills_source = "stored"
        if not essential and not elective and jd_data.get("job_description"):
            try:
                from controllers import ExtractionController
                fallback = ExtractionController().extract_classified_skills(
                    jd_data.get("job_description") or ""
                )
                essential = list(fallback.get("essential", []) or [])
                elective = list(fallback.get("elective", []) or [])
                if essential or elective:
                    skills_source = "heuristic_fallback"
                    logger.warning(
                        f"[ATS] JD {jd_id} had empty stored skills; "
                        f"served heuristic split "
                        f"({len(essential)} essential, {len(elective)} elective)."
                    )
            except Exception as repair_err:
                logger.warning(f"[ATS] skill read-repair failed for JD {jd_id}: {repair_err}")
        company = jd.company
        # Personalized skill overlap for the logged-in candidate (if token present).
        # Public browsing still works without auth — these fields are just omitted.
        matched_essential: list = []
        missing_essential: list = list(essential)
        matched_elective: list = []
        missing_elective: list = list(elective)
        candidate_skills: list = []
        try:
            auth = request.headers.get("authorization") or request.headers.get("Authorization")
            if auth and auth.lower().startswith("bearer "):
                from jose import jwt as _jwt
                from helpers.config import get_settings as _get_settings
                _settings = _get_settings()
                payload = _jwt.decode(
                    auth.split(" ", 1)[1], _settings.JWT_SECRET_KEY,
                    algorithms=[_settings.JWT_ALGORITHM],
                )
                user_id = payload.get("sub")
                if user_id:
                    from models.sql_models import CandidateDocument
                    cust = db.query(CustomerProfile).filter_by(user_id=user_id).first()
                    if cust is not None:
                        doc = (
                            db.query(CandidateDocument)
                            .filter_by(customer_id=cust.id, is_primary=1).first()
                            or db.query(CandidateDocument)
                            .filter_by(customer_id=cust.id).first()
                        )
                        if doc is not None:
                            from controllers import VectorDBController
                            from controllers.VectorDBController import CANDIDATE_COLLECTION
                            from controllers.SkillNormalizer import (
                                normalize_skill as _canon_one,
                                match_skills as _match_skills,
                            )
                            coll = VectorDBController()._get_collection(CANDIDATE_COLLECTION)
                            cdata = coll.get(
                                where={"file_id": doc.vector_id},
                                include=["metadatas"],
                            )
                            cset = set()
                            for meta in (cdata.get("metadatas") or []):
                                for s in (meta.get("skills") or "").split(","):
                                    v = _canon_one(s)
                                    if v:
                                        cset.add(v)
                            candidate_skills = sorted(cset)
                            matched_essential, missing_essential, _ = _match_skills(cset, essential)
                            matched_elective, missing_elective, _ = _match_skills(cset, elective)
        except Exception as person_err:
            logger.warning(f"[ATS] personalized skill overlap skipped for JD {jd_id}: {person_err}")
        return JSONResponse(content={
            "jd_id": jd.id,
            "jd_name": jd.jd_name,
            "location": jd.location,
            "job_type": {"id": jd.job_type.id, "name": jd.job_type.name} if jd.job_type else None,
            "job_function": {"id": jd.job_function.id, "name": jd.job_function.name} if jd.job_function else None,
            "is_public": jd.is_public,
            "created_at": jd.created_at.isoformat(),
            "company": {
                "company_id": company.id if company else None,
                "company_name": company.company_name if company else None,
                "description": company.description if company else None,
                "website": getattr(company, "website", None) if company else None,
                "industry": getattr(company, "industry", None) if company else None,
                "location": getattr(company, "location", None) if company else None,
                "company_logo_url": f"/ats/companies/{company.id}/logo" if company and getattr(company, "photo_path", None) else None,
            },
            "job_description": jd_data.get("job_description"),
            "essential_skills": essential,
            "elective_skills": elective,
            "skills_source": skills_source,
            "required_experience": jd_data.get("required_experience", 0.0),
            "candidate_skills": candidate_skills,
            "matched_essential_skills": matched_essential,
            "missing_essential_skills": missing_essential,
            "matched_elective_skills": matched_elective,
            "missing_elective_skills": missing_elective,
        })
    except Exception as e:
        logger.error(f"Error fetching public job detail: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.get("/companies/{company_id}/logo")
async def get_company_logo(company_id: str, db: Session = Depends(get_db)):
    """Serve a company's profile logo. Public (job details are publicly browsable)."""
    try:
        company = db.query(CompanyProfile).filter_by(id=company_id).first()
        photo_path = getattr(company, "photo_path", None) if company else None
        if not photo_path or not os.path.exists(photo_path):
            return JSONResponse(status_code=404, content={"message": "Company logo not found."})
        media_type, _ = mimetypes.guess_type(photo_path)
        return FileResponse(path=photo_path, media_type=media_type or "application/octet-stream")
    except Exception as e:
        logger.error(f"Error serving company logo: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.get("/candidates/{customer_id}/photo")
async def get_candidate_photo_for_company(
    customer_id: str,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    """Serve a candidate's profile photo to a company (visible pre-contact). | Target: Company"""
    try:
        profile = db.query(CustomerProfile).filter_by(id=customer_id).first()
        photo_path = getattr(profile, "photo_path", None) if profile else None
        if not photo_path or not os.path.exists(photo_path):
            return JSONResponse(status_code=404, content={"message": "Candidate photo not found."})
        media_type, _ = mimetypes.guess_type(photo_path)
        return FileResponse(path=photo_path, media_type=media_type or "application/octet-stream")
    except Exception as e:
        logger.error(f"Error serving candidate photo: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.post("/jobs/{jd_id}/apply")
async def apply_to_job(
    jd_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """Candidate applies to a public job, placed in APPLIED stage. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        
        jd = db.query(JobDescription).filter_by(id=jd_id).first()
        if not jd:
            return JSONResponse(status_code=404, content={"message": "Job not found."})

        # Check if already applied or contacted
        existing = db.query(JobApplication).filter_by(customer_id=customer_id, jd_id=jd_id).first()
        if existing:
            return JSONResponse(status_code=400, content={"message": "You have already applied or been contacted for this job."})

        new_app = JobApplication(
            company_id=jd.company_id,
            customer_id=customer_id,
            jd_id=jd_id,
            stage=PipelineStage.APPLIED
        )
        db.add(new_app)
        db.commit()

        return JSONResponse(status_code=201, content={"message": "Successfully applied to job.", "application_id": new_app.id})
    except Exception as e:
        db.rollback()
        logger.error(f"Error applying to job: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.get("/customer/applications")
async def list_my_applications(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """View all jobs the candidate applied to or was contacted for. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        apps = db.query(JobApplication).filter_by(customer_id=customer_id).all()

        results = []
        for app in apps:
            results.append({
                "application_id": app.id,
                "company_name": app.company.company_name if app.company else None,
                "jd_id": app.jd_id,
                "jd_name": app.job_description.jd_name if app.job_description else None,
                "stage": app.stage.value,
                "created_at": app.created_at.isoformat()
            })
        return JSONResponse(content={"applications": results})
    except Exception as e:
        logger.error(f"Error listing applications: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.put("/customer/applications/{application_id}/accept")
async def accept_company_contact(
    application_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """Accept a company contact request, moves CONTACTED to CONSIDERED. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        app = db.query(JobApplication).filter_by(id=application_id, customer_id=customer_id).first()

        if not app:
            return JSONResponse(status_code=404, content={"message": "Application not found."})
        
        if app.stage != PipelineStage.CONTACTED:
            return JSONResponse(status_code=400, content={"message": "Can only accept applications in the CONTACTED stage."})

        app.stage = PipelineStage.CONSIDERED
        db.commit()

        return JSONResponse(content={"message": "Request accepted. You are now being considered.", "stage": app.stage.value})
    except Exception as e:
        db.rollback()
        logger.error(f"Error accepting request: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.put("/customer/applications/{application_id}/decline")
async def decline_company_contact(
    application_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """Decline a company contact request, moves CONTACTED to CANCELLED. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        app = db.query(JobApplication).filter_by(id=application_id, customer_id=customer_id).first()

        if not app:
            return JSONResponse(status_code=404, content={"message": "Application not found."})

        if app.stage != PipelineStage.CONTACTED:
            return JSONResponse(status_code=400, content={"message": "Can only decline applications in the CONTACTED stage."})

        app.stage = PipelineStage.CANCELLED
        db.commit()

        return JSONResponse(content={"message": "Request declined.", "stage": app.stage.value})
    except Exception as e:
        db.rollback()
        logger.error(f"Error declining request: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

# ---------------------------------------------------------
# CANDIDATE AI ADVICE
# ---------------------------------------------------------

@ats_router.get("/jobs/{jd_id}/apply-advice")
async def get_apply_advice(
    jd_id: str,
    force: int = 0,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """LLM verdict on whether the candidate should apply. Cached per CV+JD. | Target: Customer"""
    try:
        customer_id = current_user.customer_profile.id
        jd = db.query(JobDescription).filter_by(id=jd_id, is_public=1).first()
        if not jd:
            return JSONResponse(status_code=404, content={"message": "Job not found."})

        doc = (
            db.query(CandidateDocument)
            .filter_by(customer_id=customer_id, is_primary=1).first()
            or db.query(CandidateDocument)
            .filter_by(customer_id=customer_id).first()
        )
        if not doc:
            return JSONResponse(status_code=400, content={"message": "Upload a CV first to get AI advice."})

        # Cache lookup (skipped with ?force=1)
        if not force:
            cached = db.query(ApplyAdviceCache).filter_by(
                customer_id=customer_id, jd_id=jd_id, document_id=doc.id
            ).first()
            if cached:
                try:
                    return JSONResponse(content={
                        "advice": json.loads(cached.advice_json),
                        "cached": True,
                        "created_at": cached.created_at.isoformat() if cached.created_at else None,
                    })
                except Exception:
                    pass  # fall through and regenerate

        from controllers import JDController
        jd_data = JDController().get_jd(jd.jd_name, company_id=jd.company_id)
        if not jd_data:
            return JSONResponse(status_code=404, content={"message": "Job details not found in vector store."})

        skills = jd_data.get("skills", {}) or {}
        essential = list(skills.get("essential", []) or [])
        elective = list(skills.get("elective", []) or [])
        if not essential and not elective and jd_data.get("job_description"):
            try:
                from controllers import ExtractionController
                fallback = ExtractionController().extract_classified_skills(
                    jd_data.get("job_description") or ""
                )
                essential = list(fallback.get("essential", []) or [])
                elective = list(fallback.get("elective", []) or [])
            except Exception as repair_err:
                logger.warning(f"[Advice] skill fallback failed for JD {jd_id}: {repair_err}")
        required_experience = jd_data.get("required_experience", 0.0) or 0.0
        job_description = jd_data.get("job_description") or ""

        from controllers import VectorDBController
        from controllers.VectorDBController import CANDIDATE_COLLECTION
        from controllers.SkillNormalizer import (
            normalize_skill as _canon_one,
            match_skills as _match_skills,
        )
        coll = VectorDBController()._get_collection(CANDIDATE_COLLECTION)
        cdata = coll.get(where={"file_id": doc.vector_id}, include=["metadatas"])
        cset = set()
        candidate_experience = 0.0
        for meta in (cdata.get("metadatas") or []):
            for s in (meta.get("skills") or "").split(","):
                v = _canon_one(s)
                if v:
                    cset.add(v)
            try:
                candidate_experience = max(candidate_experience, float(meta.get("experience_years", 0) or 0))
            except Exception:
                pass
        candidate_skills = sorted(cset)
        matched_essential, missing_essential, _ = _match_skills(cset, essential)
        matched_elective, missing_elective, _ = _match_skills(cset, elective)

        from controllers import LLMExtractionController
        llm_extraction = LLMExtractionController()
        if not llm_extraction.is_available:
            return JSONResponse(
                status_code=503,
                content={"message": "AI advice unavailable (LLM not configured)."},
            )

        from stores.llm.templates.template_parser import TemplateParser
        from helpers.config import get_settings
        settings = get_settings()
        parser = TemplateParser(language=settings.PRIMARY_LANG, default_language=settings.DEFAULT_LANG)
        system_prompt = parser.get("apply_advice", "system_prompt")
        user_prompt = parser.get("apply_advice", "user_prompt", vars={
            "jd_name": jd.jd_name,
            "company_name": jd.company.company_name if jd.company else "",
            "location": jd.location or "",
            "required_experience": str(required_experience),
            "candidate_experience": str(candidate_experience),
            "essential_skills": ", ".join(essential) or "not specified",
            "elective_skills": ", ".join(elective) or "none",
            "candidate_skills": ", ".join(candidate_skills) or "none",
            "matched_essential": ", ".join(matched_essential) or "none",
            "missing_essential": ", ".join(missing_essential) or "none",
            "matched_elective": ", ".join(matched_elective) or "none",
            "job_description": job_description[:4000],
        })
        if not system_prompt or not user_prompt:
            return JSONResponse(status_code=500, content={"message": "Advice prompts not found."})

        from stores.llm import LLMProvider
        provider = LLMProvider(
            api_key=settings.GENERATION_API_KEY,
            api_url=settings.GENERATION_API_URL,
            model_id=settings.GENERATION_MODEL_ID,
            max_tokens=settings.GENERATION_MAX_TOKENS,
            temperature=settings.GENERATION_TEMPERATURE,
        )
        raw = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt,
                                max_tokens=800, temperature=0.3)
        if not raw or not raw.strip():
            return JSONResponse(status_code=502, content={"message": "AI returned an empty response."})
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()
        try:
            advice = json.loads(cleaned)
        except Exception:
            logger.warning(f"[Advice] LLM returned non-JSON for JD {jd_id}: {raw[:200]}")
            return JSONResponse(status_code=502, content={"message": "AI returned an unreadable response."})

        if not isinstance(advice, dict) or advice.get("verdict") not in ("APPLY", "MAYBE", "SKIP"):
            return JSONResponse(status_code=502, content={"message": "AI returned an unreadable response."})

        # Upsert cache (per CV+JD)
        existing = db.query(ApplyAdviceCache).filter_by(
            customer_id=customer_id, jd_id=jd_id, document_id=doc.id
        ).first()
        payload = json.dumps(advice)
        if existing:
            existing.advice_json = payload
        else:
            db.add(ApplyAdviceCache(
                customer_id=customer_id, jd_id=jd_id,
                document_id=doc.id, advice_json=payload,
            ))
        db.commit()

        return JSONResponse(content={"advice": advice, "cached": False})
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating apply advice: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

# ---------------------------------------------------------
# COMPANY ACTIONS
# ---------------------------------------------------------

@ats_router.post("/company/contact")
async def company_contact_candidate(
    payload: CreateRequest,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """Company reaches out to a candidate from AI Match, placed in CONTACTED stage. | Target: Company"""
    try:
        company_id = current_user.company_profile.id

        jd = db.query(JobDescription).filter_by(id=payload.jd_id, company_id=company_id).first()
        if not jd:
            return JSONResponse(status_code=404, content={"message": "Job description not found."})

        existing = db.query(JobApplication).filter_by(customer_id=payload.customer_id, jd_id=payload.jd_id).first()
        if existing:
            return JSONResponse(status_code=400, content={"message": "Candidate is already in the pipeline for this job."})

        new_app = JobApplication(
            company_id=company_id,
            customer_id=payload.customer_id,
            jd_id=payload.jd_id,
            stage=PipelineStage.CONTACTED
        )
        db.add(new_app)
        db.commit()

        return JSONResponse(status_code=201, content={"message": "Candidate contacted successfully.", "application_id": new_app.id})
    except Exception as e:
        db.rollback()
        logger.error(f"Error contacting candidate: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.get("/board/{jd_id}")
async def get_kanban_board(
    jd_id: str,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """Returns the Kanban board data for a job grouped by pipeline stage. | Target: Company"""
    try:
        company_id = current_user.company_profile.id
        
        jd = db.query(JobDescription).filter_by(id=jd_id, company_id=company_id).first()
        if not jd:
            return JSONResponse(status_code=404, content={"message": "Job description not found."})

        apps = db.query(JobApplication).filter_by(jd_id=jd_id).all()

        board = {
            PipelineStage.APPLIED.value: [],
            PipelineStage.CONTACTED.value: [],
            PipelineStage.CONSIDERED.value: [],
            PipelineStage.INTERVIEWING.value: [],
            PipelineStage.OFFER_SENT.value: [],
            PipelineStage.HIRED.value: [],
            PipelineStage.REJECTED.value: [],
            PipelineStage.CANCELLED.value: []
        }

        for app in apps:
            customer = app.customer
            customer_user = customer.user if customer else None
            board[app.stage.value].append({
                "application_id": app.id,
                "candidate_id": app.customer_id,
                "candidate_name": customer.name if customer else None,
                "candidate_email": customer_user.email if customer_user else None,
                "candidate_phone": customer.phone if customer else None,
                "match_score": app.match_score,
                "created_at": app.created_at.isoformat()
            })

        return JSONResponse(content={"jd_name": jd.jd_name, "board": board})
    except Exception as e:
        logger.error(f"Error fetching Kanban board: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})

@ats_router.put("/board/{application_id}/move")
async def move_candidate_stage(
    application_id: str,
    payload: MoveCandidate,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """Company drags a candidate to a new pipeline stage (e.g. Interviewing). | Target: Company"""
    try:
        company_id = current_user.company_profile.id
        app = db.query(JobApplication).filter_by(id=application_id, company_id=company_id).first()

        if not app:
            return JSONResponse(status_code=404, content={"message": "Application not found."})

        app.stage = payload.stage
        db.commit()

        return JSONResponse(content={"message": f"Candidate moved to {payload.stage.value}.", "stage": app.stage.value})
    except Exception as e:
        db.rollback()
        logger.error(f"Error moving candidate: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
