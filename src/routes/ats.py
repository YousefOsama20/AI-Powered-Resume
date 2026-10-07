from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

from stores.db.database import get_db
from models.sql_models import User, JobApplication, JobDescription, PipelineStage, CustomerProfile
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
    """
    Candidates can browse public job descriptions to apply.
    """
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

@ats_router.post("/jobs/{jd_id}/apply")
async def apply_to_job(
    jd_id: str,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """
    Candidate applies to a public job. Places them in the APPLIED column.
    """
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
    """
    Customer views all jobs they applied to or were contacted for.
    """
    try:
        customer_id = current_user.customer_profile.id
        apps = db.query(JobApplication).filter_by(customer_id=customer_id).all()

        results = []
        for app in apps:
            results.append({
                "application_id": app.id,
                "company_name": app.company.company_name,
                "jd_name": app.job_description.jd_name,
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
    """
    Customer accepts a company's contact request. Moves from CONTACTED to CONSIDERED.
    """
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

# ---------------------------------------------------------
# COMPANY ACTIONS
# ---------------------------------------------------------

@ats_router.post("/company/contact")
async def company_contact_candidate(
    payload: CreateRequest,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """
    Company reaches out to a candidate from the Match pool. Places in CONTACTED column.
    """
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
    """
    Returns the Kanban board data for a specific job, grouped by stage.
    """
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
            board[app.stage.value].append({
                "application_id": app.id,
                "candidate_id": app.customer_id,
                "candidate_name": app.customer.name,
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
    """
    Company drags and drops a candidate to a new pipeline stage.
    """
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
