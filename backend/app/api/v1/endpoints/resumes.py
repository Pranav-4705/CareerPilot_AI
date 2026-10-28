import os
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeParseResponse,
    ResumeHistoryItem,
    ResumeResponse,
)
from app.schemas.analysis import ResumeAnalysisResponse
from app.schemas.ats import ATSAnalysisResponse
from app.services.resume_service import save_resume_file
from app.services.parser_service import extract_text_from_file
from app.services.extractor_service import extract_structured_resume_data
from app.services.ats_service import calculate_ats_analysis

router = APIRouter()


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload candidate resume (PDF or DOCX)",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file in PDF or DOCX format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Securely uploads a candidate's resume (PDF or DOCX), validates extension,
    MIME type, file integrity, and size limits, then persists the record in the database
    with incremented user-scoped version number and active status.
    """
    file_bytes = await file.read()
    resume = save_resume_file(
        db=db,
        user=current_user,
        file=file,
        file_bytes=file_bytes,
    )

    return ResumeUploadResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        version_number=resume.version_number,
        is_active=resume.is_active,
        uploaded_at=resume.uploaded_at,
        status="uploaded",
        message="Resume uploaded successfully",
    )


@router.get(
    "",
    response_model=List[ResumeHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Get candidate resume upload history",
)
def get_resume_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieves the authenticated user's resume history, ordered newest first,
    including version numbers, active status, and parsing/analysis state.
    """
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc(), Resume.version_number.desc())
        .all()
    )

    history_items = []
    for r in resumes:
        is_parsed = bool(r.extracted_text and r.extracted_text.strip())
        analyses = r.analyses or []
        has_analysis = len(analyses) > 0
        ats_score = None
        has_ats_score = False

        if has_analysis:
            for a in analyses:
                if a.ats_score is not None:
                    ats_score = a.ats_score
                    has_ats_score = True
                    break

        item_status = "analyzed" if has_ats_score or has_analysis else ("parsed" if is_parsed else "uploaded")

        history_items.append(
            ResumeHistoryItem(
                id=r.id,
                original_filename=r.original_filename,
                version_number=r.version_number,
                is_active=r.is_active,
                uploaded_at=r.uploaded_at,
                status=item_status,
                is_parsed=is_parsed,
                has_analysis=has_analysis,
                has_ats_score=has_ats_score,
                ats_score=ats_score,
            )
        )

    return history_items


@router.get(
    "/active",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get candidate's currently active resume",
)
def get_active_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Returns the authenticated user's currently active resume version.
    Returns 404 if no resume has been uploaded yet.
    """
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id, Resume.is_active == True)
        .order_by(Resume.version_number.desc())
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active resume found for the current user.",
        )
    return resume


@router.post(
    "/{resume_id}/activate",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Set a specific resume version as active",
)
def activate_resume_version(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Sets the specified resume as the candidate's active resume.
    Deactivates any previous active resume for the candidate.
    Enforces user ownership and preserves all analysis data.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # 1. Deactivate all resumes for this user
    db.query(Resume).filter(Resume.user_id == current_user.id).update({"is_active": False})

    # 2. Activate target resume
    resume.is_active = True
    db.commit()
    db.refresh(resume)

    return resume


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific resume version",
)
def delete_resume_version(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Deletes a specific resume version and its associated file on disk.
    If the deleted resume was active, automatically promotes the newest remaining version to active.
    Enforces strict user ownership.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    was_active = resume.is_active
    file_path = resume.file_path

    # 1. Remove stored local file from disk if present
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            # Non-blocking log if file cleanup fails
            pass

    # 2. Delete database record (cascades to ResumeAnalysis and JobMatch)
    db.delete(resume)
    db.flush()

    promoted_active_id: Optional[int] = None
    # 3. If deleted resume was active, promote the newest remaining version
    if was_active:
        remaining_newest = (
            db.query(Resume)
            .filter(Resume.user_id == current_user.id)
            .order_by(Resume.uploaded_at.desc(), Resume.version_number.desc())
            .first()
        )
        if remaining_newest:
            remaining_newest.is_active = True
            promoted_active_id = remaining_newest.id

    db.commit()

    return {
        "message": f"Resume version #{resume_id} deleted successfully",
        "id": resume_id,
        "promoted_active_id": promoted_active_id,
    }


@router.post(
    "/{resume_id}/parse",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse stored resume file and extract plain text",
)
def parse_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Extracts plain text from a previously uploaded PDF or DOCX resume,
    cleans whitespace/formatting, and stores the extracted text in the database.
    Enforces user ownership.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    extracted_text = extract_text_from_file(resume.file_path)
    resume.extracted_text = extracted_text
    db.commit()
    db.refresh(resume)

    return ResumeParseResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        version_number=resume.version_number,
        is_active=resume.is_active,
        status="parsed",
        extracted_text_length=len(extracted_text),
        message="Resume parsed and text extracted successfully",
    )


@router.post(
    "/{resume_id}/analyze",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured information from parsed resume text",
)
def analyze_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Extracts structured entities (Skills, Education, Work Experience, Projects, Certifications)
    from the parsed resume text using deterministic rule-based NLP techniques.
    Enforces user ownership and requires that the resume has been parsed first.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    if not resume.extracted_text or not resume.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been parsed yet. Please parse the resume before analyzing.",
        )

    structured_data = extract_structured_resume_data(resume.extracted_text)

    # Check if an analysis record already exists for this resume or create new
    analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume.id).first()
    if not analysis:
        analysis = ResumeAnalysis(
            resume_id=resume.id,
            extracted_skills=structured_data["extracted_skills"],
            education=structured_data["education"],
            experience=structured_data["experience"],
            projects=structured_data["projects"],
            certifications=structured_data["certifications"],
        )
        db.add(analysis)
    else:
        analysis.extracted_skills = structured_data["extracted_skills"]
        analysis.education = structured_data["education"]
        analysis.experience = structured_data["experience"]
        analysis.projects = structured_data["projects"]
        analysis.certifications = structured_data["certifications"]

    db.commit()
    db.refresh(analysis)

    return ResumeAnalysisResponse(
        id=analysis.id,
        resume_id=analysis.resume_id,
        extracted_skills=analysis.extracted_skills or [],
        education=analysis.education or [],
        experience=analysis.experience or [],
        projects=analysis.projects or [],
        certifications=analysis.certifications or [],
        created_at=analysis.created_at,
        message="Resume structured analysis completed successfully",
    )


@router.post(
    "/{resume_id}/ats-analyze",
    response_model=ATSAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute transparent ATS score and actionable recommendations",
)
def ats_analyze_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Computes a deterministic ATS score (0-100) and actionable recommendations based on
    resume structure, skills coverage, keyword quality, experience depth, and readability.
    Requires that the resume has been structurally analyzed first.
    """
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
            detail="Resume has not been structurally analyzed yet. Please run structured analysis first.",
        )

    raw_text = resume.extracted_text or ""
    ats_results = calculate_ats_analysis(analysis, raw_text)

    # Persist ATS results into database
    analysis.ats_score = ats_results["ats_score"]
    analysis.missing_skills = ats_results["missing_skills"]
    analysis.recommendations = ats_results["recommendations"]

    db.commit()
    db.refresh(analysis)

    return ATSAnalysisResponse(
        id=analysis.id,
        resume_id=resume.id,
        ats_score=ats_results["ats_score"],
        component_scores=ats_results["component_scores"],
        strengths=ats_results["strengths"],
        weaknesses=ats_results["weaknesses"],
        missing_skills=ats_results["missing_skills"],
        recommendations=ats_results["recommendations"],
        created_at=analysis.created_at,
        message="ATS analysis completed successfully",
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get resume details and extracted text",
)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieves a resume's metadata and extracted text.
    Enforces user ownership.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return resume
