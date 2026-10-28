import io
import fitz
from fastapi import status
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis


def get_auth_token(client, email="analyzer.user@example.com", name="Analyzer User"):
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


def create_full_test_resume_pdf() -> bytes:
    """Generates a complete structured resume PDF with all sections."""
    text = """
Jane Candidate
Senior Full Stack Engineer | San Francisco, CA | jane@example.com

TECHNICAL SKILLS
Programming Languages: Python, TypeScript, JavaScript, SQL, Bash
Frameworks & Libraries: FastAPI, Next.js, React, Django, Tailwind CSS, PyTorch
Databases: PostgreSQL, Redis, MongoDB
Cloud & DevOps: Docker, Kubernetes, AWS, Git, CI/CD, Linux
Concepts: REST API, Microservices, Machine Learning, Agile

WORK EXPERIENCE
Senior Software Engineer at TechCorp
Jan 2022 - Present | San Francisco, CA
- Architected and deployed microservices using FastAPI and PostgreSQL handling 50k requests/min.
- Spearheaded migration to Next.js and Tailwind CSS improving web load times by 40%.
- Implemented automated CI/CD pipelines using GitHub Actions and Docker.

Full Stack Developer at CloudStartup
June 2019 - Dec 2021 | Austin, TX
- Developed REST APIs in Python and integrated frontend React dashboards.
- Managed PostgreSQL database schemas and optimized indexing.

PROJECTS
CareerPilot AI Platform
- Built end-to-end recruitment platform using Next.js, FastAPI, and PostgreSQL.
- Implemented real-time resume parsing and skills extraction pipeline.

Autonomous Data Pipeline
- Designed distributed data ingestion pipeline using Python, Redis, and Docker.

EDUCATION
Bachelor of Science in Computer Science
University of California, Berkeley | 2015 - 2019
- Dean's Honors List, Magna Cum Laude.

CERTIFICATIONS
- AWS Certified Solutions Architect - Associate
- Certified Kubernetes Administrator (CKA)
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_full_structured_resume_analysis(client, db_session):
    """Test full structured analysis of a comprehensive resume."""
    token = get_auth_token(client, email="full.analysis@example.com")
    pdf_bytes = create_full_test_resume_pdf()

    # 1. Upload
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("full_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    resume_id = upload_res.json()["id"]

    # 2. Parse
    parse_res = client.post(
        f"/api/v1/resumes/{resume_id}/parse",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert parse_res.status_code == status.HTTP_200_OK

    # 3. Analyze
    analyze_res = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analyze_res.status_code == status.HTTP_200_OK
    data = analyze_res.json()

    assert data["resume_id"] == resume_id
    assert "id" in data

    # Skills Verification
    skills = data["extracted_skills"]
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Next.js" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "AWS" in skills
    assert "TypeScript" in skills

    # Education Verification
    education = data["education"]
    assert len(education) >= 1
    edu_text = str(education)
    assert "Bachelor of Science in Computer Science" in edu_text or "Berkeley" in edu_text

    # Experience Verification
    experience = data["experience"]
    assert len(experience) >= 1
    exp_text = str(experience)
    assert "Senior Software Engineer" in exp_text or "TechCorp" in exp_text

    # Projects Verification
    projects = data["projects"]
    assert len(projects) >= 1
    proj_text = str(projects)
    assert "CareerPilot AI" in proj_text or "Autonomous Data Pipeline" in proj_text

    # Certifications Verification
    certifications = data["certifications"]
    assert len(certifications) >= 1
    cert_text = str(certifications)
    assert "AWS Certified Solutions Architect" in cert_text or "Kubernetes" in cert_text

    # DB Persistence Verification
    db_analysis = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id).first()
    assert db_analysis is not None
    assert "Python" in db_analysis.extracted_skills
    assert len(db_analysis.education) >= 1
    assert len(db_analysis.experience) >= 1


def test_missing_sections_handled_gracefully(client):
    """Test resume with only skills and experience handles missing education/projects/certifications."""
    token = get_auth_token(client, email="minimal.analysis@example.com")
    
    text = """
Alex Developer
TECHNICAL SKILLS:
Python, FastAPI, SQL, Docker

EXPERIENCE:
Software Engineer at Beta Inc.
2021 - 2023
- Built backend APIs with FastAPI and Docker.
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("minimal_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = upload_res.json()["id"]

    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})

    analyze_res = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analyze_res.status_code == status.HTTP_200_OK
    data = analyze_res.json()

    assert "Python" in data["extracted_skills"]
    assert "FastAPI" in data["extracted_skills"]
    assert len(data["experience"]) >= 1
    # Missing sections should be empty lists without error
    assert data["education"] == []
    assert data["projects"] == []
    assert data["certifications"] == []


def test_analyze_unparsed_resume_fails(client):
    """Test that attempting to analyze an uploaded resume before parsing returns 400."""
    token = get_auth_token(client, email="unparsed@example.com")
    
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Sample text")
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("unparsed.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = upload_res.json()["id"]

    # Directly analyze without calling parse
    analyze_res = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analyze_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "not been parsed" in analyze_res.json()["detail"].lower()


def test_analyze_another_users_resume_fails(client):
    """Test that a user cannot analyze another user's resume (returns 404)."""
    token1 = get_auth_token(client, email="user.one@example.com", name="User One")
    token2 = get_auth_token(client, email="user.two@example.com", name="User Two")

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "User One Resume\nSkills: Python, FastAPI")
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("user1.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    resume_id = upload_res.json()["id"]

    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token1}"})

    # User 2 attempts to analyze User 1's resume
    analyze_res = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert analyze_res.status_code == status.HTTP_404_NOT_FOUND


def test_avoid_invented_information(client):
    """Test that skills or data not mentioned in the resume are never extracted or hallucinated."""
    token = get_auth_token(client, email="strict.test@example.com")
    
    text = """
David Clean
SKILLS:
Python, SQLite

EXPERIENCE:
Junior Developer at Alpha Co.
- Maintained Python backend scripts.
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("david_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = upload_res.json()["id"]

    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})

    analyze_res = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analyze_res.status_code == status.HTTP_200_OK
    skills = analyze_res.json()["extracted_skills"]

    # Only present skills
    assert "Python" in skills
    assert "SQLite" in skills

    # Unmentioned skills MUST NOT be hallucinated or present
    assert "Kubernetes" not in skills
    assert "React" not in skills
    assert "Next.js" not in skills
    assert "Java" not in skills
    assert "AWS" not in skills
    assert "TensorFlow" not in skills
