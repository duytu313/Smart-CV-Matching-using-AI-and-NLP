"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ Auth Schemas ============

class UserRole(str, Enum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.CANDIDATE
    company_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (no password)."""
    id: int
    email: str
    full_name: str
    role: str
    company_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for auth token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============ Resume Schemas ============

class ResumeCreate(BaseModel):
    """Schema for creating a resume entry."""
    title: str
    raw_text: Optional[str] = None


class ResumeResponse(BaseModel):
    """Schema for resume response."""
    id: int
    user_id: int
    title: str
    raw_text: Optional[str]
    skills: Optional[List[str]]
    experience_years: Optional[float]
    education: Optional[List[Dict]]
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    """Response after uploading and parsing a resume."""
    id: int
    title: str
    parsed_text: str
    extracted_skills: List[str]
    experience_years: Optional[float]
    education: List[Dict]
    contact_info: Dict


class CVAnalysisRequest(BaseModel):
    """Request for CV analysis."""
    resume_text: str


class CVAnalysisResponse(BaseModel):
    """Response for CV analysis."""
    skills: List[str]
    skills_by_category: Dict[str, List[str]]
    experience_years: Optional[float]
    education: List[Dict]
    contact_info: Dict
    skill_suggestions: List[str]


# ============ Job Schemas ============

class JobCreate(BaseModel):
    """Schema for creating a job posting."""
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None  # full-time, part-time, contract
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: str
    requirements: Optional[str] = None
    required_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None


class JobUpdate(BaseModel):
    """Schema for updating a job posting."""
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    is_active: Optional[bool] = None


class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    recruiter_id: int
    title: str
    company: str
    location: Optional[str]
    job_type: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    description: str
    requirements: Optional[str]
    required_skills: Optional[List[str]]
    preferred_skills: Optional[List[str]]
    experience_min: Optional[int]
    experience_max: Optional[int]
    is_active: bool
    views_count: int
    applications_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for paginated job list."""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ Application Schemas ============

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


class ApplicationCreate(BaseModel):
    """Schema for creating a job application."""
    job_id: int
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None


class ApplicationUpdate(BaseModel):
    """Schema for updating application status (recruiter)."""
    status: ApplicationStatus
    recruiter_notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    """Schema for application response."""
    id: int
    candidate_id: int
    job_id: int
    resume_id: Optional[int]
    status: str
    cover_letter: Optional[str]
    match_score: Optional[float]
    matched_skills: Optional[List[str]]
    missing_skills: Optional[List[str]]
    recruiter_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Nested data
    job: Optional[JobResponse] = None
    candidate: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# ============ Recommendation Schemas ============

class RecommendationRequest(BaseModel):
    """Request for job recommendations."""
    resume_id: Optional[int] = None
    resume_text: Optional[str] = None
    k: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=30.0, ge=0, le=100)


class JobMatchResponse(BaseModel):
    """Schema for a single job match."""
    job_id: int
    title: str
    company: str
    location: Optional[str]
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    skill_match_percentage: float
    recommendation_reason: str
    job_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None


class RecommendationResponse(BaseModel):
    """Response for job recommendations."""
    recommendations: List[JobMatchResponse]
    total_jobs_searched: int
    resume_skills: List[str]


class MatchExplanationRequest(BaseModel):
    """Request for detailed match explanation."""
    resume_id: Optional[int] = None
    resume_text: Optional[str] = None
    job_id: int


class MatchExplanationResponse(BaseModel):
    """Detailed match explanation response."""
    job: Dict[str, Any]
    overall_score: float
    semantic_similarity: float
    skill_analysis: Dict[str, Any]
    matched_skills_by_category: Dict[str, List[str]]
    missing_skills_by_category: Dict[str, List[str]]
    skill_suggestions: List[str]


# ============ Evaluation Schemas ============

class EvaluationRequest(BaseModel):
    """Request for evaluating recommendation quality."""
    recommended_job_ids: List[int]
    relevant_job_ids: List[int]
    k: int = Field(default=10, ge=1, le=50)


class EvaluationResponse(BaseModel):
    """Response with evaluation metrics."""
    precision_at_k: float
    recall_at_k: float
    f1_at_k: float
    ndcg_at_k: float
    map_at_k: float
    mrr: float
    hit_rate: float
    k: int
    num_relevant: int
    num_recommended: int


# ============ Dashboard Schemas ============

class CandidateDashboardResponse(BaseModel):
    """Dashboard data for candidates."""
    user: UserResponse
    resumes: List[ResumeResponse]
    applications: List[ApplicationResponse]
    recommendations: List[JobMatchResponse]
    stats: Dict[str, Any]


class RecruiterDashboardResponse(BaseModel):
    """Dashboard data for recruiters."""
    user: UserResponse
    jobs: List[JobResponse]
    recent_applications: List[ApplicationResponse]
    stats: Dict[str, Any]
