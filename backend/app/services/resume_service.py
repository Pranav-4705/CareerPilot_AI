import os
import re
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.resume import Resume
from app.models.user import User

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",
}


def sanitize_filename(filename: str) -> str:
    """
    Strips directory paths and special characters from the original filename.
    """
    clean_name = os.path.basename(filename)
    clean_name = re.sub(r"[^\w\s.-]", "", clean_name).strip()
    return clean_name or "resume"


def validate_resume_file(file: UploadFile, file_bytes: bytes) -> Tuple[str, str]:
    """
    Validates file extension, MIME type, and size constraints.
    Returns (cleaned_original_filename, file_extension).
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing.",
        )

    # 1. Validate extension
    _, ext = os.path.splitext(file.filename)
    ext_lower = ext.lower()
    if ext_lower not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Only PDF and DOCX files are supported.",
        )

    # 2. Validate MIME type if provided
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'. Only PDF and DOCX documents are accepted.",
        )

    # 3. Validate file size
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"File size ({len(file_bytes) / (1024 * 1024):.2f}MB) exceeds "
                f"the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            ),
        )

    # 4. Validate header magic bytes
    if ext_lower == ".pdf" and not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupt or invalid PDF file header.",
        )
    elif ext_lower == ".docx" and not file_bytes.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupt or invalid DOCX file header.",
        )

    clean_original = sanitize_filename(file.filename)
    return clean_original, ext_lower


def save_resume_file(
    db: Session,
    user: User,
    file: UploadFile,
    file_bytes: bytes,
) -> Resume:
    """
    Saves the uploaded file to disk with a secure unique filename,
    manages user-scoped versioning (increments version and sets is_active=True,
    deactivates previous versions), and creates a linked Resume database record.
    """
    clean_original, ext = validate_resume_file(file, file_bytes)

    # Generate unique stored filename: <uuid>_<safe_original_basename>.<ext>
    base_name, _ = os.path.splitext(clean_original)
    safe_base = re.sub(r"\s+", "_", base_name)[:50]
    unique_filename = f"{uuid.uuid4().hex}_{safe_base}{ext}"

    # Ensure upload directory exists
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    stored_file_path = os.path.join(upload_dir, unique_filename)

    # Write file bytes to disk
    with open(stored_file_path, "wb") as f:
        f.write(file_bytes)

    # Store relative path for portability across environments
    relative_path = os.path.join(settings.UPLOAD_DIR, unique_filename).replace("\\", "/")

    # 1. Determine next version number for this user
    max_version = (
        db.query(func.max(Resume.version_number))
        .filter(Resume.user_id == user.id)
        .scalar()
    )
    next_version = (max_version or 0) + 1

    # 2. Deactivate previous active resumes of this user
    db.query(Resume).filter(
        Resume.user_id == user.id,
        Resume.is_active == True,
    ).update({"is_active": False})

    # 3. Create new active Resume database record
    resume = Resume(
        user_id=user.id,
        original_filename=clean_original,
        file_path=relative_path,
        version_number=next_version,
        is_active=True,
        extracted_text=None,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return resume
