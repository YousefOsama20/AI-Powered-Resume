from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from stores.db.database import get_db
from models.sql_models import User, CustomerProfile, CompanyProfile, UserRole
from routes.schemes.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from helpers.security import get_password_hash, verify_password, create_access_token
from helpers.config import get_settings

settings = get_settings()
auth_router = APIRouter(
    prefix="/auth",
    tags=["api_v1", "Authentication"]
)

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user (Customer or Company) and create their profile. | Target: Both"""
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )

    # Create new User
    new_user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=request.role
    )
    db.add(new_user)
    db.flush() # Flush to get the new_user.id

    # Create associated profile
    if request.role == UserRole.CUSTOMER:
        profile = CustomerProfile(user_id=new_user.id, name=request.name)
        db.add(profile)
    elif request.role == UserRole.COMPANY:
        profile = CompanyProfile(user_id=new_user.id, company_name=request.name)
        db.add(profile)
    elif request.role == UserRole.ADMIN:
        # Admins might not need a specific profile, or can be handled later
        pass

    db.commit()
    db.refresh(new_user)
    
    return new_user

@auth_router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email/password and return a JWT token. | Target: Both"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role}, expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token, role=user.role)
