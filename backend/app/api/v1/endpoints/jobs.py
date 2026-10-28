from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.models.job_description import JobDescription
from app.models.job_match import JobMatch
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobAnalyzeResponse,
    JobMatchResponse,
)
from app.schemas.match_insights import MatchInsightsResponse
from app.services.job_service import (
    normalize_job_text,
    analyze_job_description_text,
)
from app.services.matching_service import perform_resume_job_match

router = APIRouter()


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new target job description",
)
def create_job(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Creates a new target job description linked to the authenticated candidate.
    Normalizes text and validates non-empty content.
    """
    clean_title = job_in.title.strip() if job_in.title else ""
    clean_company = job_in.company.strip() if job_in.company else None
    normalized_desc = normalize_job_text(job_in.description)

    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job title cannot be empty.",
        )

    if not normalized_desc or len(normalized_desc) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description cannot be empty or whitespace-only.",
        )

    job = JobDescription(
        user_id=current_user.id,
        title=clean_title,
        company=clean_company,
        description=normalized_desc,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get(
    "",
    response_model=List[JobResponse],
    status_code=status.HTTP_200_OK,
    summary="List all job descriptions for current user",
)
def get_user_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieves all job descriptions created by the authenticated candidate,
    ordered newest first.
    """
    jobs = (
        db.query(JobDescription)
        .filter(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
        .all()
    )
    return jobs


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get job description details",
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieves a job description by ID. Enforces candidate ownership.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )
    return job


@router.post(
    "/{job_id}/analyze",
    response_model=JobAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured requirements and skills from job description",
)
def analyze_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Analyzes job description to deterministically extract:
    - Required technical skills
    - Explicit experience requirements
    - Explicit education qualifications
    - Core responsibilities
    - Domain keywords
    Enforces candidate ownership.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    analysis_data = analyze_job_description_text(
        title=job.title,
        company=job.company or "",
        description=job.description,
    )

    # Persist structured extraction to job record
    job.extracted_skills = analysis_data["extracted_skills"]
    job.extracted_keywords = analysis_data["extracted_keywords"]
    job.required_experience = analysis_data["required_experience"]
    job.education_requirements = analysis_data["education_requirements"]
    job.responsibilities = analysis_data["responsibilities"]

    db.commit()
    db.refresh(job)

    exp_signals = []
    if isinstance(job.required_experience, dict):
        exp_signals = job.required_experience.get("signals", [])
    elif isinstance(job.required_experience, list):
        exp_signals = job.required_experience

    return JobAnalyzeResponse(
        id=job.id,
        job_id=job.id,
        required_skills=job.extracted_skills or [],
        experience_requirements=exp_signals,
        education_requirements=job.education_requirements or [],
        responsibilities=job.responsibilities or [],
        extracted_keywords=job.extracted_keywords or [],
        message="Job description analysis completed successfully",
    )


@router.post(
    "/{job_id}/match/{resume_id}",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Match a candidate resume against a target job description",
)
def match_resume_to_job(
    job_id: int,
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Performs deterministic 4-component weighted resume-to-job matching:
    - Skills Match (50%)
    - Experience Match (20%)
    - Education Match (10%)
    - Responsibility / Keyword Alignment (20%)
    Enforces candidate ownership on both job description and resume.
    """
    # 1. Verify Job ownership
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    # 2. Verify Resume ownership
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # 3. Verify Resume has been parsed and analyzed
    if not resume.extracted_text or not resume.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been parsed yet. Please parse the resume first.",
        )

    analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been structurally analyzed yet. Please analyze the resume first.",
        )

    # 4. If job has not been structurally analyzed yet, analyze automatically
    if not job.extracted_skills:
        analysis_data = analyze_job_description_text(job.title, job.company or "", job.description)
        job.extracted_skills = analysis_data["extracted_skills"]
        job.extracted_keywords = analysis_data["extracted_keywords"]
        job.required_experience = analysis_data["required_experience"]
        job.education_requirements = analysis_data["education_requirements"]
        job.responsibilities = analysis_data["responsibilities"]
        db.commit()
        db.refresh(job)

    # 5. Perform Matching Engine Pipeline
    results = perform_resume_job_match(
        resume=resume,
        analysis=analysis,
        job=job,
    )

    # 6. Persist JobMatch Record
    job_match = db.query(JobMatch).filter(
        JobMatch.resume_id == resume.id,
        JobMatch.job_description_id == job.id,
    ).first()

    if not job_match:
        job_match = JobMatch(
            user_id=current_user.id,
            resume_id=resume.id,
            job_description_id=job.id,
            match_score=results["match_score"],
            matched_skills=results["matched_skills"],
            missing_skills=results["missing_skills"],
            keyword_gaps=results["keyword_gaps"],
            recommendations=results["recommendations"],
        )
        db.add(job_match)
    else:
        job_match.user_id = current_user.id
        job_match.match_score = results["match_score"]
        job_match.matched_skills = results["matched_skills"]
        job_match.missing_skills = results["missing_skills"]
        job_match.keyword_gaps = results["keyword_gaps"]
        job_match.recommendations = results["recommendations"]

    db.commit()
    db.refresh(job_match)

    return JobMatchResponse(
        id=job_match.id,
        user_id=job_match.user_id,
        resume_id=job_match.resume_id,
        job_description_id=job_match.job_description_id,
        match_score=job_match.match_score,
        component_scores=results["component_scores"],
        skill_match_score=results["skill_match_score"],
        semantic_similarity_score=results["semantic_similarity_score"],
        matched_skills=job_match.matched_skills or [],
        missing_skills=job_match.missing_skills or [],
        keyword_gaps=job_match.keyword_gaps or [],
        experience_match=results["experience_match"],
        education_match=results["education_match"],
        recommendations=job_match.recommendations or [],
        created_at=job_match.created_at,
        message="Resume and job matched successfully",
    )


@router.get(
    "/{job_id}/match/{resume_id}/insights",
    response_model=MatchInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed candidate gap insights, prioritized skills, and recommendations",
)
def get_job_match_insights(
    job_id: int,
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieves deep deterministic insights for an existing job-resume match:
    - Prioritized missing skills (High, Medium, Low)
    - 4-state Experience evaluation (meets, does_not_meet, unknown, not_specified)
    - 4-state Education evaluation (meets, does_not_meet, unknown, not_specified)
    - Responsibility aligned vs improvement areas
    - Actionable recommendations with severity tags
    - Candidate strengths for the role
    Enforces ownership on both job and resume.
    """
    # 1. Verify Job ownership
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    # 2. Verify Resume ownership
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been structurally analyzed yet.",
        )

    # 3. Retrieve existing JobMatch record
    job_match = db.query(JobMatch).filter(
        JobMatch.resume_id == resume.id,
        JobMatch.job_description_id == job.id,
    ).first()

    if not job_match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No match record found for this job and resume. Please run match first.",
        )

    # 4. Generate deterministic insights
    from app.services.match_insights_service import generate_match_insights
    insights = generate_match_insights(
        job=job,
        resume=resume,
        analysis=analysis,
        job_match=job_match,
    )

    return insights
