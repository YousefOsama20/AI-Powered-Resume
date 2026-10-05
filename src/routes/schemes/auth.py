from pydantic import BaseModel, EmailStr
from typing import Optional
from models.sql_models import UserRole

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole
    
    # Common field for profile
    name: str  # For customer it's their name, for company it's company_name

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
    
    class Config:
        from_attributes = True
