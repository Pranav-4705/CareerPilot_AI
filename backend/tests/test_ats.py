import io
import fitz
from fastapi import status
from app.models.resume_analysis import ResumeAnalysis


def get_auth_token(client, email="ats.tester@example.com", name="ATS Tester"):
    """Helper to register and login a test user."""
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


def create_strong_resume_pdf() -> bytes:
    """Generates an exceptional, highly-structured resume with metrics and action verbs."""
    text = """
Sarah Connor
Lead Software Architect | sarah@example.com | (555) 019-2834 | San Francisco, CA

TECHNICAL SKILLS
Languages: Python, TypeScript, JavaScript, SQL, Bash, Go
Frameworks: FastAPI, Next.js, React, Django, Node.js, Tailwind CSS
Databases & Cloud: PostgreSQL, Redis, MongoDB, AWS, Docker, Kubernetes, CI/CD, Git, Linux
Architecture: Microservices, REST API, GraphQL, Machine Learning, Agile, System Design

WORK EXPERIENCE
Staff Software Engineer at CloudScale Systems
Jan 2021 - Present | San Francisco, CA
- Architected and deployed distributed FastAPI microservices handling over 50k req/min with 99.99% uptime.
- Optimized PostgreSQL database indexes and query caching, reducing query latency by 45%.
- Spearheaded engineering migration to Next.js and TypeScript, increasing page speed by 35%.
- Automated end-to-end CI/CD delivery pipelines using Docker and GitHub Actions, cutting build times by 60%.

Senior Full Stack Engineer at FinTech Global
Mar 2018 - Dec 2020 | New York, NY
- Engineered secure REST APIs in Python and integrated real-time React analytics dashboards for 200k active users.
- Led a team of 6 engineers to launch payment processing workflows generating $12M in annual revenue.
- Implemented robust unit and integration testing suite achieving 92% code coverage.

PROJECTS
CareerPilot AI Recruitment Platform
- Developed AI-powered recruitment readiness platform with FastAPI, PostgreSQL, and Next.js.
- Deployed containerized microservices on AWS with automated health monitoring.

EDUCATION
Master of Science in Computer Science
Stanford University | 2016 - 2018

Bachelor of Science in Software Engineering
UC Berkeley | 2012 - 2016

CERTIFICATIONS
- AWS Certified Solutions Architect - Professional
- Certified Kubernetes Administrator (CKA)
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sparse_incomplete_resume_pdf() -> bytes:
    """Generates an incomplete resume missing education, metrics, certifications, and depth."""
    text = """
Bob Minimal
SKILLS:
Python, HTML

EXPERIENCE:
Worked on web pages at SmallCo.
Did some coding.
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_strong_ats_analysis_score_and_bounds(client, db_session):
    """Test that a strong resume achieves a high score and satisfies 0 <= score <= 100."""
    token = get_auth_token(client, email="strong.ats@example.com")
    pdf_bytes = create_strong_resume_pdf()

    # 1. Upload
    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("strong_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]

    # 2. Parse & Structural Analyze
    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token}"})

    # 3. ATS Analyze
    ats_res = client.post(
        f"/api/v1/resumes/{resume_id}/ats-analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ats_res.status_code == status.HTTP_200_OK
    data = ats_res.json()

    # Score verification
    score = data["ats_score"]
    assert 0.0 <= score <= 100.0
    assert score >= 80.0, f"Expected high ATS score for strong resume, got {score}"

    # Component scores verification
    comps = data["component_scores"]
    assert comps["section_structure"] >= 90.0
    assert comps["skills_coverage"] >= 90.0
    assert comps["keyword_quality"] >= 80.0
    assert comps["experience_depth"] >= 80.0
    assert comps["readability_format"] >= 80.0

    # Strengths check
    assert len(data["strengths"]) >= 3

    # DB verification
    db_analysis = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == resume_id).first()
    assert db_analysis.ats_score == score


def test_strong_vs_incomplete_score_differential(client):
    """Test that a strong resume scores significantly higher than a sparse, incomplete resume."""
    token1 = get_auth_token(client, email="candidate.high@example.com")
    token2 = get_auth_token(client, email="candidate.low@example.com")

    # High quality resume
    up1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("high.pdf", io.BytesIO(create_strong_resume_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    id1 = up1.json()["id"]
    client.post(f"/api/v1/resumes/{id1}/parse", headers={"Authorization": f"Bearer {token1}"})
    client.post(f"/api/v1/resumes/{id1}/analyze", headers={"Authorization": f"Bearer {token1}"})
    ats1 = client.post(f"/api/v1/resumes/{id1}/ats-analyze", headers={"Authorization": f"Bearer {token1}"}).json()

    # Incomplete resume
    up2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("low.pdf", io.BytesIO(create_sparse_incomplete_resume_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {token2}"},
    )
    id2 = up2.json()["id"]
    client.post(f"/api/v1/resumes/{id2}/parse", headers={"Authorization": f"Bearer {token2}"})
    client.post(f"/api/v1/resumes/{id2}/analyze", headers={"Authorization": f"Bearer {token2}"})
    ats2 = client.post(f"/api/v1/resumes/{id2}/ats-analyze", headers={"Authorization": f"Bearer {token2}"}).json()

    assert ats1["ats_score"] > ats2["ats_score"]
    assert (ats1["ats_score"] - ats2["ats_score"]) >= 35.0


def test_missing_sections_and_recommendations_alignment(client):
    """Test that missing sections create weaknesses and specific recommendations."""
    token = get_auth_token(client, email="missing.sections@example.com")
    pdf_bytes = create_sparse_incomplete_resume_pdf()

    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("sparse.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]

    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token}"})

    ats_res = client.post(
        f"/api/v1/resumes/{resume_id}/ats-analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ats_res.status_code == status.HTTP_200_OK
    data = ats_res.json()

    # Weaknesses should detect missing education and few skills
    weaknesses_str = " ".join(data["weaknesses"]).lower()
    assert "education" in weaknesses_str
    assert "skills" in weaknesses_str or "metrics" in weaknesses_str

    # Recommendations should advise adding education
    recs_str = " ".join(data["recommendations"]).lower()
    assert "education" in recs_str


def test_missing_skills_detection(client):
    """Test that absent industry baseline skills are reported in missing_skills."""
    token = get_auth_token(client, email="skills.gap@example.com")
    pdf_bytes = create_sparse_incomplete_resume_pdf()

    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("gap.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]

    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token}"})

    ats_res = client.post(
        f"/api/v1/resumes/{resume_id}/ats-analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = ats_res.json()

    assert len(data["missing_skills"]) > 0
    assert any(s in ["PostgreSQL", "Docker", "AWS", "Git", "REST API", "CI/CD"] for s in data["missing_skills"])


def test_unanalyzed_resume_rejected(client):
    """Test calling ats-analyze on a resume that hasn't been structurally analyzed returns 400."""
    token = get_auth_token(client, email="not.analyzed@example.com")
    pdf_bytes = create_strong_resume_pdf()

    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("not_analyzed.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]

    # Try calling ats-analyze directly without running structured analysis
    ats_res = client.post(
        f"/api/v1/resumes/{resume_id}/ats-analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ats_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "structurally analyzed" in ats_res.json()["detail"].lower()


def test_cannot_ats_analyze_another_users_resume(client):
    """Test that a user cannot run ats-analyze on another user's resume (returns 404)."""
    token1 = get_auth_token(client, email="user.alpha@example.com", name="User Alpha")
    token2 = get_auth_token(client, email="user.beta@example.com", name="User Beta")

    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("alpha.pdf", io.BytesIO(create_strong_resume_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    resume_id = up_res.json()["id"]

    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token1}"})
    client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token1}"})

    # User Beta tries to analyze User Alpha's resume
    ats_res = client.post(
        f"/api/v1/resumes/{resume_id}/ats-analyze",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert ats_res.status_code == status.HTTP_404_NOT_FOUND
