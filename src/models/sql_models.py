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

class PipelineStage(str, enum.Enum):
    APPLIED = "APPLIED"           # Candidate applied to the job
    CONTACTED = "CONTACTED"       # Company reached out to candidate (formerly PENDING)
    CONSIDERED = "CONSIDERED"     # Candidate accepted contact, or Company moved them forward
    INTERVIEWING = "INTERVIEWING" # Interview scheduled/happening
    OFFER_SENT = "OFFER_SENT"     # Job offer sent
    HIRED = "HIRED"               # Candidate accepted offer
    REJECTED = "REJECTED"         # Candidate rejected by company or vice versa
    CANCELLED = "CANCELLED"       # Application withdrawn

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
    photo_path = Column(String, nullable=True)

    user = relationship("User", back_populates="customer_profile")
    job_types = relationship("JobType", secondary=customer_job_type)
    job_functions = relationship("JobFunction", secondary=customer_job_function)
    applications = relationship("JobApplication", back_populates="customer", foreign_keys="[JobApplication.customer_id]")
    documents = relationship("CandidateDocument", back_populates="customer", cascade="all, delete-orphan")

class CandidateDocument(Base):
    __tablename__ = "candidate_documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customer_profiles.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    vector_id = Column(String, nullable=False) # Maps to ChromaDB ID
    is_primary = Column(Integer, default=0) # 1 for True, 0 for False
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("CustomerProfile", back_populates="documents")
    applications = relationship("JobApplication", back_populates="document")

class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    company_name = Column(String, nullable=False)
    description = Column(Text)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    location = Column(String, nullable=True)
    photo_path = Column(String, nullable=True)

    user = relationship("User", back_populates="company_profile")
    applications = relationship("JobApplication", back_populates="company", foreign_keys="[JobApplication.company_id]")
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
    is_public = Column(Integer, default=1) # 1 for public (candidates can apply), 0 for private
    location = Column(String, nullable=True)
    job_type_id = Column(String, ForeignKey("job_types.id"), nullable=True)
    job_function_id = Column(String, ForeignKey("job_functions.id"), nullable=True)

    job_type = relationship("JobType")
    job_function = relationship("JobFunction")

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("CompanyProfile", back_populates="jds")
    applications = relationship("JobApplication", back_populates="job_description", cascade="all, delete-orphan")

class JobType(Base):
    __tablename__ = "job_types"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False) # e.g. "Full Time", "Remote"

class JobFunction(Base):
    __tablename__ = "job_functions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False) # e.g. "Software Engineering"

class JobApplication(Base):
    """
    Represents an ATS Pipeline entity linking a Candidate to a Job Description.
    """
    __tablename__ = "job_applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("company_profiles.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customer_profiles.id"), nullable=False)
    jd_id = Column(String, ForeignKey("job_descriptions.id"), nullable=False)
    document_id = Column(String, ForeignKey("candidate_documents.id"), nullable=True)
    
    stage = Column(Enum(PipelineStage), default=PipelineStage.APPLIED)
    match_score = Column(Integer, nullable=True) # Optional caching of AI match score
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("CompanyProfile", foreign_keys=[company_id], back_populates="applications")
    customer = relationship("CustomerProfile", foreign_keys=[customer_id], back_populates="applications")
    job_description = relationship("JobDescription", back_populates="applications")
    document = relationship("CandidateDocument", back_populates="applications")

class ApplyAdviceCache(Base):
    """
    Cached per-candidate-per-JD LLM apply advice.
    Cache key is (customer_id, jd_id, document_id): a new CV upload
    (new document) naturally invalidates old advice.
    """
    __tablename__ = "apply_advice_cache"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customer_profiles.id"), nullable=False)
    jd_id = Column(String, ForeignKey("job_descriptions.id"), nullable=False)
    document_id = Column(String, ForeignKey("candidate_documents.id"), nullable=False)
    advice_json = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
