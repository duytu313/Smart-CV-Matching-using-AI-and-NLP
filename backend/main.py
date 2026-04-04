"""
AI-Powered Job Recommendation System - FastAPI Backend
Main application with all API endpoints.
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import os

from models.database import (
    get_db, create_tables, User, UserRole as DBUserRole, 
    Resume, Job, Application, ApplicationStatus as DBApplicationStatus, Recommendation
)
from services import (
    EmbeddingService, SkillService, RecommendationService, 
    CVParser, EvaluationService, AuthService
)
from services.recommendation_service import recommendation_service
from schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    ResumeCreate, ResumeResponse, ResumeUploadResponse,
    CVAnalysisRequest, CVAnalysisResponse,
    JobCreate, JobUpdate, JobResponse, JobListResponse,
    ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    RecommendationRequest, RecommendationResponse, JobMatchResponse,
    MatchExplanationRequest, MatchExplanationResponse,
    EvaluationRequest, EvaluationResponse,
    CandidateDashboardResponse, RecruiterDashboardResponse
)


# Initialize FastAPI app
app = FastAPI(
    title="AI Job Recommender API",
    description="AI-powered job recommendation system with resume parsing and skill matching",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Dependency Functions ============

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate user from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    token_data = AuthService.decode_token(token)
    
    if not token_data or AuthService.is_token_expired(token_data):
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get user if authenticated, otherwise return None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        token_data = AuthService.decode_token(token)
        if token_data and not AuthService.is_token_expired(token_data):
            return db.query(User).filter(User.id == token_data.user_id).first()
    except:
        pass
    return None


def require_role(role: DBUserRole):
    """Dependency to require a specific user role."""
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"Requires {role.value} role")
        return user
    return role_checker


# ============ Health Check ============

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "job-recommender-api"}


# ============ Auth Endpoints ============

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (candidate or recruiter)."""
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = AuthService.hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=DBUserRole(user_data.role.value),
        company_name=user_data.company_name
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate token
    token = AuthService.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value
    )
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_name=user.company_name,
            created_at=user.created_at
        )
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not AuthService.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    token = AuthService.create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value
    )
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_name=user.company_name,
            created_at=user.created_at
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        company_name=user.company_name,
        created_at=user.created_at
    )


# ============ Resume/CV Endpoints ============

@app.post("/api/upload-cv", response_model=ResumeUploadResponse)
async def upload_cv(
    file: UploadFile = File(...),
    title: str = Query(default="My Resume"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a CV/resume file.
    Supports: PDF, DOCX, TXT, and image files (PNG, JPG, JPEG, BMP, TIFF, WEBP)
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Mở rộng allowed extensions để bao gồm ảnh
    allowed_extensions = ['.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    content = await file.read()
    
    try:
        # Parse the resume (giờ đã hỗ trợ ảnh)
        parsed = CVParser.parse_resume(content, file.filename)
        
        # Generate embedding
        embedding = EmbeddingService.generate_embedding(parsed.raw_text)
        embedding_bytes = EmbeddingService.embedding_to_bytes(embedding) if embedding is not None else None
        
        # Save to database
        resume = Resume(
            user_id=user.id,
            title=title,
            raw_text=parsed.raw_text,
            skills=parsed.skills,
            experience_years=parsed.experience_years,
            education=parsed.education,
            parsed_data=parsed.sections,
            embedding=embedding_bytes,
            is_primary=not db.query(Resume).filter(Resume.user_id == user.id).first()
        )
        
        db.add(resume)
        db.commit()
        db.refresh(resume)
        
        return ResumeUploadResponse(
            id=resume.id,
            title=resume.title,
            parsed_text=parsed.raw_text[:2000] + "..." if len(parsed.raw_text) > 2000 else parsed.raw_text,
            extracted_skills=parsed.skills,
            experience_years=parsed.experience_years,
            education=parsed.education,
            contact_info=parsed.contact_info
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error parsing file: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")


@app.get("/api/resumes", response_model=List[ResumeResponse])
async def get_user_resumes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all resumes for the current user."""
    resumes = db.query(Resume).filter(Resume.user_id == user.id).all()
    return resumes


@app.get("/api/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return resume


# ============ NEW: Set Resume as Primary Endpoint ============

@app.put("/api/resumes/{resume_id}/set-primary", response_model=ResumeResponse)
async def set_resume_primary(
    resume_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set a resume as the primary resume for the user."""
    # Find the resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Set all other resumes of this user to not primary
    db.query(Resume).filter(
        Resume.user_id == user.id
    ).update({"is_primary": False})
    
    # Set this resume as primary
    resume.is_primary = True
    
    db.commit()
    db.refresh(resume)
    
    return resume


# ============ Alternative: PATCH endpoint for updating resume ============

@app.patch("/api/resumes/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    update_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a resume (e.g., set is_primary, update title, etc.)."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # If setting as primary, unset all others first
    if update_data.get("is_primary"):
        db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.id != resume_id
        ).update({"is_primary": False})
    
    # Update fields
    for key, value in update_data.items():
        if hasattr(resume, key):
            setattr(resume, key, value)
    
    db.commit()
    db.refresh(resume)
    
    return resume


# ============ NEW: Delete Resume Endpoint ============

@app.delete("/api/resumes/{resume_id}")
async def delete_resume(
    resume_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a resume (owner only)."""
    # Find the resume
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Check if this is the only resume
    user_resumes = db.query(Resume).filter(Resume.user_id == user.id).count()
    
    # If deleting primary resume and there are other resumes, set another as primary
    if resume.is_primary and user_resumes > 1:
        another_resume = db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.id != resume_id
        ).first()
        if another_resume:
            another_resume.is_primary = True
    
    # Delete the resume
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}


@app.post("/api/analyze-cv", response_model=CVAnalysisResponse)
async def analyze_cv(request: CVAnalysisRequest):
    """Analyze CV text and extract skills, education, etc."""
    if not request.resume_text:
        raise HTTPException(status_code=400, detail="Resume text is required")
    
    # Extract skills
    skills = SkillService.extract_skills(request.resume_text)
    skills_by_category = SkillService.categorize_skills(skills)
    
    # Extract other information
    experience_years = CVParser.extract_experience_years(request.resume_text)
    education = CVParser.extract_education(request.resume_text)
    contact_info = CVParser.extract_contact_info(request.resume_text)
    
    # Suggest skills
    skill_suggestions = SkillService.suggest_skills(skills)
    
    return CVAnalysisResponse(
        skills=skills,
        skills_by_category=skills_by_category,
        experience_years=experience_years,
        education=education,
        contact_info=contact_info,
        skill_suggestions=skill_suggestions
    )


# ============ Job Endpoints ============

@app.post("/api/jobs", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    user: User = Depends(require_role(DBUserRole.RECRUITER)),
    db: Session = Depends(get_db)
):
    """Create a new job posting (recruiters only)."""
    # Generate embedding
    job_text = f"{job_data.title} {job_data.description} {job_data.requirements or ''}"
    embedding = EmbeddingService.generate_embedding(job_text)
    embedding_bytes = EmbeddingService.embedding_to_bytes(embedding) if embedding is not None else None
    
    job = Job(
        recruiter_id=user.id,
        title=job_data.title,
        company=job_data.company,
        location=job_data.location,
        job_type=job_data.job_type,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        description=job_data.description,
        requirements=job_data.requirements,
        required_skills=job_data.required_skills,
        preferred_skills=job_data.preferred_skills,
        experience_min=job_data.experience_min,
        experience_max=job_data.experience_max,
        embedding=embedding_bytes
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Add to recommendation index
    recommendation_service.index_job(job.id, {
        'id': job.id,
        'title': job.title,
        'company': job.company,
        'description': job.description,
        'requirements': job.requirements,
        'required_skills': job.required_skills or [],
        'preferred_skills': job.preferred_skills or []
    })
    
    return job


@app.get("/api/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    skills: Optional[str] = None,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """List all active jobs with filtering and pagination."""
    query = db.query(Job).filter(Job.is_active == True)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Job.title.ilike(search_term)) |
            (Job.company.ilike(search_term)) |
            (Job.description.ilike(search_term))
        )
    
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    
    if job_type:
        query = query.filter(Job.job_type == job_type)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    jobs = query.order_by(Job.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific job by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Increment view count
    job.views_count += 1
    db.commit()
    
    return job


@app.put("/api/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    user: User = Depends(require_role(DBUserRole.RECRUITER)),
    db: Session = Depends(get_db)
):
    """Update a job posting (owner only)."""
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == user.id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not authorized")
    
    # Update fields
    update_data = job_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)
    
    # Regenerate embedding if description changed
    if 'description' in update_data or 'requirements' in update_data:
        job_text = f"{job.title} {job.description} {job.requirements or ''}"
        embedding = EmbeddingService.generate_embedding(job_text)
        job.embedding = EmbeddingService.embedding_to_bytes(embedding) if embedding is not None else None
    
    db.commit()
    db.refresh(job)
    
    return job


@app.delete("/api/jobs/{job_id}")
async def delete_job(
    job_id: int,
    user: User = Depends(require_role(DBUserRole.RECRUITER)),
    db: Session = Depends(get_db)
):
    """Delete a job posting (owner only)."""
    job = db.query(Job).filter(Job.id == job_id, Job.recruiter_id == user.id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not authorized")
    
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully"}


# ============ Application Endpoints ============

@app.post("/api/apply", response_model=ApplicationResponse)
async def apply_to_job(
    application: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply to a job."""
    # Check if job exists
    job = db.query(Job).filter(Job.id == application.job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not active")
    
    # Check if already applied
    existing = db.query(Application).filter(
        Application.candidate_id == user.id,
        Application.job_id == application.job_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this job")
    
    # Get resume for skill matching
    resume = None
    match_score = None
    matched_skills = None
    missing_skills = None
    
    if application.resume_id:
        resume = db.query(Resume).filter(
            Resume.id == application.resume_id,
            Resume.user_id == user.id
        ).first()
    else:
        # Use primary resume
        resume = db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.is_primary == True
        ).first()
    
    if resume:
        # Calculate match score
        skill_analysis = SkillService.calculate_skill_score(
            resume.skills or [],
            job.required_skills or [],
            job.preferred_skills
        )
        match_score = skill_analysis['total_score']
        matched_skills = skill_analysis['all_matched']
        missing_skills = skill_analysis['all_missing']
    
    # Create application
    app_record = Application(
        candidate_id=user.id,
        job_id=application.job_id,
        resume_id=resume.id if resume else None,
        cover_letter=application.cover_letter,
        match_score=match_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills
    )
    
    db.add(app_record)
    
    # Update job applications count
    job.applications_count += 1
    
    db.commit()
    db.refresh(app_record)
    
    return app_record


@app.get("/api/applications", response_model=List[ApplicationResponse])
async def get_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get applications for current user (candidates: their applications, recruiters: applications to their jobs)."""
    if user.role == DBUserRole.CANDIDATE:
        applications = db.query(Application).filter(
            Application.candidate_id == user.id
        ).order_by(Application.created_at.desc()).all()
    else:
        # Get applications to recruiter's jobs
        applications = db.query(Application).join(Job).filter(
            Job.recruiter_id == user.id
        ).order_by(Application.created_at.desc()).all()
    
    # Load related data
    for app in applications:
        app.job = db.query(Job).filter(Job.id == app.job_id).first()
        if user.role == DBUserRole.RECRUITER:
            app.candidate = db.query(User).filter(User.id == app.candidate_id).first()
    
    return applications


@app.put("/api/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    update_data: ApplicationUpdate,
    user: User = Depends(require_role(DBUserRole.RECRUITER)),
    db: Session = Depends(get_db)
):
    """Update application status (recruiters only)."""
    application = db.query(Application).join(Job).filter(
        Application.id == application_id,
        Job.recruiter_id == user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application.status = DBApplicationStatus(update_data.status.value)
    if update_data.recruiter_notes:
        application.recruiter_notes = update_data.recruiter_notes
    
    db.commit()
    db.refresh(application)
    
    return application


# ============ Recommendation Endpoints ============

@app.post("/api/recommend-jobs", response_model=RecommendationResponse)
async def recommend_jobs(
    request: RecommendationRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered job recommendations based on resume."""
    resume_text = request.resume_text
    resume_skills = []
    
    # Get resume from database if ID provided
    if request.resume_id and user:
        resume = db.query(Resume).filter(
            Resume.id == request.resume_id,
            Resume.user_id == user.id
        ).first()
        if resume:
            resume_text = resume.raw_text
            resume_skills = resume.skills or []
    
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume text or valid resume_id required")
    
    # Extract skills if not from database
    if not resume_skills:
        resume_skills = SkillService.extract_skills(resume_text)
    
    # Load jobs into index if empty
    if not recommendation_service.job_cache:
        jobs = db.query(Job).filter(Job.is_active == True).all()
        for job in jobs:
            recommendation_service.index_job(job.id, {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'description': job.description,
                'requirements': job.requirements,
                'required_skills': job.required_skills or [],
                'preferred_skills': job.preferred_skills or [],
                'job_type': job.job_type,
                'salary_min': job.salary_min,
                'salary_max': job.salary_max
            })
    
    # Get recommendations
    matches = recommendation_service.recommend_jobs(
        resume_text=resume_text,
        resume_skills=resume_skills,
        k=request.k,
        min_score=request.min_score / 100  # Convert to 0-1 range
    )
    
    # Convert to response format
    recommendations = []
    for match in matches:
        job_data = recommendation_service.job_cache.get(match.job_id, {})
        recommendations.append(JobMatchResponse(
            job_id=match.job_id,
            title=match.title,
            company=match.company,
            location=job_data.get('location'),
            match_score=match.match_score,
            matched_skills=match.matched_skills,
            missing_skills=match.missing_skills,
            skill_match_percentage=match.skill_match_percentage,
            recommendation_reason=match.recommendation_reason,
            job_type=job_data.get('job_type'),
            salary_min=job_data.get('salary_min'),
            salary_max=job_data.get('salary_max')
        ))
    
    return RecommendationResponse(
        recommendations=recommendations,
        total_jobs_searched=len(recommendation_service.job_cache),
        resume_skills=resume_skills
    )


@app.post("/api/match-explanation", response_model=MatchExplanationResponse)
async def get_match_explanation(
    request: MatchExplanationRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get detailed explanation of why a job matches a resume."""
    resume_text = request.resume_text
    resume_skills = []
    
    if request.resume_id and user:
        resume = db.query(Resume).filter(
            Resume.id == request.resume_id,
            Resume.user_id == user.id
        ).first()
        if resume:
            resume_text = resume.raw_text
            resume_skills = resume.skills or []
    
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume text or valid resume_id required")
    
    if not resume_skills:
        resume_skills = SkillService.extract_skills(resume_text)
    
    # Ensure job is in cache
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if request.job_id not in recommendation_service.job_cache:
        recommendation_service.index_job(job.id, {
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'description': job.description,
            'requirements': job.requirements,
            'required_skills': job.required_skills or [],
            'preferred_skills': job.preferred_skills or []
        })
    
    explanation = recommendation_service.get_match_explanation(
        resume_text=resume_text,
        resume_skills=resume_skills,
        job_id=request.job_id
    )
    
    if not explanation:
        raise HTTPException(status_code=404, detail="Could not generate explanation")
    
    return MatchExplanationResponse(**explanation)


# ============ Evaluation Endpoints ============

@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_recommendations(request: EvaluationRequest):
    """Evaluate recommendation quality using standard metrics."""
    result = EvaluationService.evaluate_recommendations(
        recommended=request.recommended_job_ids,
        relevant=set(request.relevant_job_ids),
        k=request.k
    )
    
    return EvaluationResponse(
        precision_at_k=result.precision_at_k,
        recall_at_k=result.recall_at_k,
        f1_at_k=result.f1_at_k,
        ndcg_at_k=result.ndcg_at_k,
        map_at_k=result.map_at_k,
        mrr=result.mrr,
        hit_rate=result.hit_rate,
        k=result.k,
        num_relevant=result.num_relevant,
        num_recommended=result.num_recommended
    )


# ============ Dashboard Endpoints ============

@app.get("/api/dashboard/candidate", response_model=CandidateDashboardResponse)
async def get_candidate_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard data for candidates."""
    # Get resumes
    resumes = db.query(Resume).filter(Resume.user_id == user.id).all()
    
    # Get applications
    applications = db.query(Application).filter(
        Application.candidate_id == user.id
    ).order_by(Application.created_at.desc()).limit(10).all()
    
    for app in applications:
        app.job = db.query(Job).filter(Job.id == app.job_id).first()
    
    # Get recommendations for primary resume
    recommendations = []
    primary_resume = next((r for r in resumes if r.is_primary), resumes[0] if resumes else None)
    
    if primary_resume and primary_resume.raw_text:
        # Load jobs if needed
        if not recommendation_service.job_cache:
            jobs = db.query(Job).filter(Job.is_active == True).all()
            for job in jobs:
                recommendation_service.index_job(job.id, {
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'description': job.description,
                    'requirements': job.requirements,
                    'required_skills': job.required_skills or [],
                    'preferred_skills': job.preferred_skills or [],
                    'job_type': job.job_type,
                    'salary_min': job.salary_min,
                    'salary_max': job.salary_max
                })
        
        matches = recommendation_service.recommend_jobs(
            resume_text=primary_resume.raw_text,
            resume_skills=primary_resume.skills or [],
            k=5
        )
        
        for match in matches:
            job_data = recommendation_service.job_cache.get(match.job_id, {})
            recommendations.append(JobMatchResponse(
                job_id=match.job_id,
                title=match.title,
                company=match.company,
                location=job_data.get('location'),
                match_score=match.match_score,
                matched_skills=match.matched_skills,
                missing_skills=match.missing_skills,
                skill_match_percentage=match.skill_match_percentage,
                recommendation_reason=match.recommendation_reason
            ))
    
    # Calculate stats
    total_applications = db.query(Application).filter(
        Application.candidate_id == user.id
    ).count()
    
    pending = db.query(Application).filter(
        Application.candidate_id == user.id,
        Application.status == DBApplicationStatus.PENDING
    ).count()
    
    shortlisted = db.query(Application).filter(
        Application.candidate_id == user.id,
        Application.status == DBApplicationStatus.SHORTLISTED
    ).count()
    
    return CandidateDashboardResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_name=user.company_name,
            created_at=user.created_at
        ),
        resumes=resumes,
        applications=applications,
        recommendations=recommendations,
        stats={
            "total_applications": total_applications,
            "pending_applications": pending,
            "shortlisted": shortlisted,
            "resumes_count": len(resumes)
        }
    )


@app.get("/api/dashboard/recruiter", response_model=RecruiterDashboardResponse)
async def get_recruiter_dashboard(
    user: User = Depends(require_role(DBUserRole.RECRUITER)),
    db: Session = Depends(get_db)
):
    """Get dashboard data for recruiters."""
    # Get jobs
    jobs = db.query(Job).filter(Job.recruiter_id == user.id).order_by(Job.created_at.desc()).all()
    
    # Get recent applications
    applications = db.query(Application).join(Job).filter(
        Job.recruiter_id == user.id
    ).order_by(Application.created_at.desc()).limit(20).all()
    
    for app in applications:
        app.job = db.query(Job).filter(Job.id == app.job_id).first()
        app.candidate = db.query(User).filter(User.id == app.candidate_id).first()
    
    # Calculate stats
    total_jobs = len(jobs)
    active_jobs = len([j for j in jobs if j.is_active])
    total_applications = sum(j.applications_count for j in jobs)
    total_views = sum(j.views_count for j in jobs)
    
    pending_review = db.query(Application).join(Job).filter(
        Job.recruiter_id == user.id,
        Application.status == DBApplicationStatus.PENDING
    ).count()
    
    return RecruiterDashboardResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_name=user.company_name,
            created_at=user.created_at
        ),
        jobs=jobs,
        recent_applications=applications,
        stats={
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applications": total_applications,
            "total_views": total_views,
            "pending_review": pending_review
        }
    )


# ============ Startup Event ============

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    try:
        create_tables()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")