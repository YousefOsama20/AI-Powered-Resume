from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from stores.db.database import Base

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    COMPANY = "COMPANY"
    ADMIN = "ADMIN"

class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

# Many-to-Many association tables for Job Types and Functions
customer_job_type = Table(
    'customer_job_type',
    Base.metadata,
    Column('customer_profile_id', String, ForeignKey('customer_profiles.id'), primary_key=True),
    Column('job_type_id', String, ForeignKey('job_types.id'), primary_key=True)
)

customer_job_function = Table(
    'customer_job_function',
    Base.metadata,
    Column('customer_profile_id', String, ForeignKey('customer_profiles.id'), primary_key=True),
    Column('job_function_id', String, ForeignKey('job_functions.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    company_profile = relationship("CompanyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    location = Column(String)
    cv_file_path = Column(String)
    cv_vector_id = Column(String) # Maps to the Global Candidate Pool ID in ChromaDB

    user = relationship("User", back_populates="customer_profile")
    job_types = relationship("JobType", secondary=customer_job_type)
    job_functions = relationship("JobFunction", secondary=customer_job_function)
    requests = relationship("CandidateRequest", back_populates="customer", foreign_keys="[CandidateRequest.customer_id]")

class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    company_name = Column(String, nullable=False)
    description = Column(Text)

    user = relationship("User", back_populates="company_profile")
    requests = relationship("CandidateRequest", back_populates="company", foreign_keys="[CandidateRequest.company_id]")
    jds = relationship("JobDescription", back_populates="company", cascade="all, delete-orphan")

class JobDescription(Base):
    """
    Lightweight SQL table to enforce ownership of JDs.
    The heavy NLP data (text, skills, embeddings) remains in ChromaDB.
    """
    __tablename__ = "job_descriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("company_profiles.id"), nullable=False)
    jd_name = Column(String, nullable=False) # Maps to the ChromaDB ID
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("CompanyProfile", back_populates="jds")

class JobType(Base):
    __tablename__ = "job_types"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False) # e.g. "Full Time", "Remote"

class JobFunction(Base):
    __tablename__ = "job_functions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False) # e.g. "Software Engineering"

class CandidateRequest(Base):
    __tablename__ = "candidate_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("company_profiles.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customer_profiles.id"), nullable=False)
    jd_id = Column(String, ForeignKey("job_descriptions.id"), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("CompanyProfile", foreign_keys=[company_id], back_populates="requests")
    customer = relationship("CustomerProfile", foreign_keys=[customer_id], back_populates="requests")
    job_description = relationship("JobDescription")
