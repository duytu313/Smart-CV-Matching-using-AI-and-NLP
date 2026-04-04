"""
Database models for the job recommendation system.
Implements SQLAlchemy ORM models for users, resumes, jobs, applications, and recommendations.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, 
    DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import os

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")

# Lazy initialization - only create engine when needed
_engine = None
_SessionLocal = None
Base = declarative_base()


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        if DATABASE_URL:
            # Ensure SSL mode for cloud databases like Neon
            db_url = DATABASE_URL
            if "sslmode" not in db_url and "neon" in db_url.lower():
                db_url = f"{db_url}?sslmode=require" if "?" not in db_url else f"{db_url}&sslmode=require"
            _engine = create_engine(db_url, pool_pre_ping=True)
        else:
            # Use SQLite for development/demo when no DATABASE_URL is set
            _engine = create_engine("sqlite:///./jobmatcher.db", connect_args={"check_same_thread": False})
    return _engine


def get_session_local():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


class UserRole(enum.Enum):
    """User roles in the system."""
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class ApplicationStatus(enum.Enum):
    """Job application status."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


class User(Base):
    """
    User model for both candidates and recruiters.
    Stores authentication credentials and profile information.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.CANDIDATE, nullable=False)
    company_name = Column(String(255), nullable=True)  # For recruiters
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


class Resume(Base):
    """
    Resume model storing CV data and embeddings.
    Supports PDF and DOCX file formats.
    """
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)  # S3 or local path
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)  # Structured resume data
    skills = Column(JSON, nullable=True)  # Extracted skills list
    experience_years = Column(Float, nullable=True)
    education = Column(JSON, nullable=True)
    embedding = Column(LargeBinary, nullable=True)  # Stored as bytes
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="resumes")
    recommendations = relationship("Recommendation", back_populates="resume", cascade="all, delete-orphan")


class Job(Base):
    """
    Job posting model with description and requirements.
    Stores job embeddings for similarity matching.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=True)  # full-time, part-time, contract
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    required_skills = Column(JSON, nullable=True)  # List of required skills
    preferred_skills = Column(JSON, nullable=True)  # List of preferred skills
    experience_min = Column(Integer, nullable=True)  # Minimum years of experience
    experience_max = Column(Integer, nullable=True)
    embedding = Column(LargeBinary, nullable=True)
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    is_active = Column(Boolean, default=True)
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recruiter = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    """
    Job application model tracking candidate applications.
    Links candidates to jobs with status tracking.
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING)
    cover_letter = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)  # AI-computed match score
    matched_skills = Column(JSON, nullable=True)
    missing_skills = Column(JSON, nullable=True)
    recruiter_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")


class Recommendation(Base):
    """
    AI-generated job recommendations for resumes.
    Stores match scores and skill analysis.
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Float, nullable=False)  # Cosine similarity score
    matched_skills = Column(JSON, nullable=True)
    missing_skills = Column(JSON, nullable=True)
    skill_match_percentage = Column(Float, nullable=True)
    experience_match = Column(Boolean, nullable=True)
    recommendation_reason = Column(Text, nullable=True)
    is_viewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    resume = relationship("Resume", back_populates="recommendations")
    job = relationship("Job", back_populates="recommendations")


class Skill(Base):
    """
    Master skill list for normalization and matching.
    Used for skill extraction and standardization.
    """
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=True)  # e.g., "programming", "soft skill"
    aliases = Column(JSON, nullable=True)  # Alternative names for the skill
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    """Dependency to get database session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=get_engine())


# Expose for import
engine = get_engine()
SessionLocal = get_session_local()