from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from stores.db.database import get_db
from models.sql_models import User, CandidateRequest, JobDescription, RequestStatus
from routes.deps import get_current_company, get_current_customer
from .schemes.requests import CreateRequest, UpdateRequestStatus

logger = logging.getLogger('uvicorn.error')

request_router = APIRouter(
    prefix="/requests",
    tags=["Candidate Requests"]
)

@request_router.post("/company")
async def create_request(
    payload: CreateRequest,
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """
    Company sends a request to a Customer for a specific Job Description.
    """
    try:
        company_id = current_user.company_profile.id

        # Verify company owns the JD
        jd = db.query(JobDescription).filter_by(id=payload.jd_id, company_id=company_id).first()
        if not jd:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Job description not found or access denied."}
            )

        # Check if request already exists
        existing = db.query(CandidateRequest).filter_by(
            company_id=company_id,
            customer_id=payload.customer_id,
            jd_id=payload.jd_id
        ).first()

        if existing:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Request already sent to this candidate for this JD."}
            )

        # Create request
        new_req = CandidateRequest(
            company_id=company_id,
            customer_id=payload.customer_id,
            jd_id=payload.jd_id,
            status=RequestStatus.PENDING
        )
        db.add(new_req)
        db.commit()
        db.refresh(new_req)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Request sent successfully.",
                "request_id": new_req.id
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating request: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )

@request_router.get("/company")
async def list_company_requests(
    current_user: User = Depends(get_current_company),
    db: Session = Depends(get_db)
    ):
    """
    List all requests sent by this company.
    """
    try:
        company_id = current_user.company_profile.id
        requests = db.query(CandidateRequest).filter_by(company_id=company_id).all()

        results = []
        for req in requests:
            results.append({
                "id": req.id,
                "customer_id": req.customer_id,
                "jd_id": req.jd_id,
                "jd_name": req.job_description.jd_name,
                "status": req.status.value,
                "created_at": req.created_at.isoformat()
            })

        return JSONResponse(content={"requests": results})
    except Exception as e:
        logger.error(f"Error listing company requests: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )

@request_router.get("/customer")
async def list_customer_requests(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """
    List all requests received by this customer.
    """
    try:
        customer_id = current_user.customer_profile.id
        requests = db.query(CandidateRequest).filter_by(customer_id=customer_id).all()

        results = []
        for req in requests:
            results.append({
                "id": req.id,
                "company_id": req.company_id,
                "company_name": req.company.company_name,
                "jd_id": req.jd_id,
                "jd_name": req.job_description.jd_name,
                "status": req.status.value,
                "created_at": req.created_at.isoformat()
            })

        return JSONResponse(content={"requests": results})
    except Exception as e:
        logger.error(f"Error listing customer requests: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )

@request_router.put("/customer/{request_id}")
async def update_request_status(
    request_id: str,
    payload: UpdateRequestStatus,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
    ):
    """
    Customer accepts or rejects a request.
    """
    try:
        customer_id = current_user.customer_profile.id
        req = db.query(CandidateRequest).filter_by(id=request_id, customer_id=customer_id).first()

        if not req:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Request not found or access denied."}
            )

        if payload.status not in [RequestStatus.ACCEPTED, RequestStatus.REJECTED]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Can only UPDATE status to ACCEPTED or REJECTED."}
            )

        req.status = payload.status
        db.commit()

        return JSONResponse(
            content={
                "message": f"Request {payload.status.value.lower()} successfully.",
                "request_id": req.id,
                "status": req.status.value
            }
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating request status: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error."}
        )
