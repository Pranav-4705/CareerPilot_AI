import io
import os
from fastapi import status
from app.models.resume import Resume
from app.models.user import User


def get_auth_token(client, email="candidate@careerpilot.ai", name="Candidate User"):
    """Helper to register and login a test user to get a Bearer token."""
    reg_payload = {
        "name": name,
        "email": email,
        "password": "Password123!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    return login_res.json()["access_token"]


def test_upload_pdf_success(client, db_session):
    """Test successful upload of a valid PDF resume."""
    token = get_auth_token(client, email="pdf.user@example.com")
    
    # Create valid mock PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Resume) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    file_payload = {
        "file": ("jane_doe_resume.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    response = client.post(
        "/api/v1/resumes/upload",
        files=file_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["original_filename"] == "jane_doe_resume.pdf"
    assert data["status"] == "uploaded"
    assert "id" in data
    assert "uploaded_at" in data

    # Verify database record
    resume_db = db_session.query(Resume).filter(Resume.id == data["id"]).first()
    assert resume_db is not None
    assert resume_db.original_filename == "jane_doe_resume.pdf"
    assert resume_db.file_path.endswith(".pdf")
    assert os.path.exists(resume_db.file_path)


def test_upload_docx_success(client, db_session):
    """Test successful upload of a valid DOCX resume."""
    token = get_auth_token(client, email="docx.user@example.com")
    
    # Create valid mock DOCX content (ZIP format starting with PK\x03\x04)
    docx_content = b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00" + b"Mock DOCX archive data"
    file_payload = {
        "file": (
            "john_smith_cv.docx",
            io.BytesIO(docx_content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    response = client.post(
        "/api/v1/resumes/upload",
        files=file_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["original_filename"] == "john_smith_cv.docx"
    assert data["status"] == "uploaded"

    resume_db = db_session.query(Resume).filter(Resume.id == data["id"]).first()
    assert resume_db is not None
    assert resume_db.original_filename == "john_smith_cv.docx"
    assert resume_db.file_path.endswith(".docx")
    assert os.path.exists(resume_db.file_path)


def test_upload_unauthorized(client):
    """Test uploading without authentication token returns 401."""
    pdf_content = b"%PDF-1.4 mock content"
    file_payload = {
        "file": ("unauth_resume.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    response = client.post("/api/v1/resumes/upload", files=file_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_unsupported_file_extension(client):
    """Test uploading file with unsupported extension (e.g. .txt) returns 400."""
    token = get_auth_token(client, email="text.user@example.com")
    
    file_payload = {
        "file": ("resume.txt", io.BytesIO(b"Just plain text resume"), "text/plain")
    }

    response = client.post(
        "/api/v1/resumes/upload",
        files=file_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "unsupported file type" in response.json()["detail"].lower()


def test_upload_invalid_corrupted_pdf_header(client):
    """Test uploading file named .pdf with invalid header returns 400."""
    token = get_auth_token(client, email="corrupt.user@example.com")
    
    file_payload = {
        "file": ("corrupted.pdf", io.BytesIO(b"NOT_A_PDF_HEADER_CONTENT"), "application/pdf")
    }

    response = client.post(
        "/api/v1/resumes/upload",
        files=file_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid pdf" in response.json()["detail"].lower()


def test_upload_oversized_file(client, monkeypatch):
    """Test uploading file larger than configured maximum size returns 413."""
    token = get_auth_token(client, email="heavy.user@example.com")
    
    # Temporarily set max upload size to 1 MB for testing
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    # 1.5 MB payload
    large_pdf_content = b"%PDF-1.4\n" + (b"0" * int(1.5 * 1024 * 1024))
    file_payload = {
        "file": ("large_resume.pdf", io.BytesIO(large_pdf_content), "application/pdf")
    }

    response = client.post(
        "/api/v1/resumes/upload",
        files=file_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert "exceeds" in response.json()["detail"].lower()


def test_user_ownership_of_uploaded_resumes(client, db_session):
    """Test that uploaded resume is accurately linked to the authenticated user's ID."""
    token1 = get_auth_token(client, email="user1@example.com", name="User One")
    token2 = get_auth_token(client, email="user2@example.com", name="User Two")

    user1_db = db_session.query(User).filter(User.email == "user1@example.com").first()
    user2_db = db_session.query(User).filter(User.email == "user2@example.com").first()

    # User 1 uploads
    pdf_content = b"%PDF-1.4 user 1 resume content"
    res1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("user1_resume.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res1.status_code == status.HTTP_201_CREATED
    resume1_id = res1.json()["id"]

    # Verify ownership in DB
    resume1_db = db_session.query(Resume).filter(Resume.id == resume1_id).first()
    assert resume1_db.user_id == user1_db.id
    assert resume1_db.user_id != user2_db.id
