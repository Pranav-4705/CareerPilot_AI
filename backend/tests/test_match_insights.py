import io
import pytest
import numpy as np
import fitz
from fastapi import status
from app.models.job_description import JobDescription
from app.models.job_match import JobMatch
from app.services.embedding_service import set_embedding_model_override


class DeterministicMockEmbeddingModel:
    """Mock SentenceTransformer model for fast, deterministic unit testing."""
    def encode(self, texts):
        embeddings = []
        for t in texts:
            seed = sum(ord(c) for c in t[:100]) % 10000
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(384).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            embeddings.append(vec)
        return np.array(embeddings)


@pytest.fixture(autouse=True)
def setup_mock_embedding():
    """Inject mock embedding model for tests and reset afterwards."""
    mock_model = DeterministicMockEmbeddingModel()
    set_embedding_model_override(mock_model)
    yield
    set_embedding_model_override(None)


def get_auth_token(client, email="insights.tester@example.com", name="Insights Tester"):
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


def create_sample_resume_pdf(skills: str = "Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux") -> bytes:
    """Creates a sample candidate resume PDF."""
    text = f"""
Taylor Dev
Senior Software Engineer | taylor@example.com

SKILLS
{skills}

WORK EXPERIENCE
Software Engineer at AlphaTech
- Built scalable backend microservices with Python, FastAPI, and PostgreSQL.
- Containerized workflows with Docker and managed Linux servers.

Backend Developer at BetaSolutions
- Developed REST APIs and database schema migrations.

EDUCATION
Bachelor of Science in Computer Science, 2021
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def setup_candidate_resume(client, token: str, skills: str = "Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux") -> int:
    """Uploads, parses, and analyzes a candidate resume."""
    pdf_bytes = create_sample_resume_pdf(skills=skills)
    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("taylor_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]
    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token}"})
    return resume_id


def test_match_insights_endpoint_success(client):
    """Test GET /api/v1/jobs/{job_id}/match/{resume_id}/insights returns deep deterministic insights."""
    token = get_auth_token(client, email="insights.success@example.com")
    resume_id = setup_candidate_resume(client, token, skills="Python, FastAPI, PostgreSQL, Docker")

    job_text = """
Senior Python Cloud Engineer

Required Qualifications:
- 3+ years of experience with Python, FastAPI, PostgreSQL, Docker.
- Required expertise in AWS, Kubernetes, and Terraform.
- Bachelor's degree in Computer Science or related technical field.

Responsibilities:
- Build high-scale microservices and REST APIs.
- Manage cloud infrastructure and CI/CD pipelines.
"""
    job_res = client.post(
        "/api/v1/jobs",
        json={"title": "Senior Python Cloud Engineer", "company": "CloudX", "description": job_text},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = job_res.json()["id"]

    # 1. Run Match first
    match_res = client.post(f"/api/v1/jobs/{job_id}/match/{resume_id}", headers={"Authorization": f"Bearer {token}"})
    assert match_res.status_code == status.HTTP_200_OK

    # 2. Fetch Insights
    ins_res = client.get(f"/api/v1/jobs/{job_id}/match/{resume_id}/insights", headers={"Authorization": f"Bearer {token}"})
    assert ins_res.status_code == status.HTTP_200_OK
    data = ins_res.json()

    # Verify structure
    assert "skill_gap" in data
    assert "experience" in data
    assert "education" in data
    assert "responsibilities" in data
    assert "recommendations" in data
    assert "strengths" in data

    # Skill Gap checks
    sg = data["skill_gap"]
    assert "Python" in sg["matched_skills"]
    assert "FastAPI" in sg["matched_skills"]
    assert "AWS" in sg["missing_skills"] or "Kubernetes" in sg["missing_skills"]
    assert len(sg["prioritized_missing_skills"]) >= 1

    # Experience status check
    assert data["experience"]["status"] in ["meets", "unknown", "does_not_meet"]
    assert "3" in str(data["experience"]["requirement"])

    # Education status check
    assert data["education"]["status"] in ["meets", "unknown"]

    # Recommendations severity check
    recs = data["recommendations"]
    assert len(recs) >= 1
    for r in recs:
        assert r["severity"] in ["critical", "high", "medium", "low", "info"]


def test_match_insights_missing_match_returns_404(client):
    """Test insights returns 404 when match has not been run yet."""
    token = get_auth_token(client, email="no.match@example.com")
    resume_id = setup_candidate_resume(client, token)

    job_res = client.post(
        "/api/v1/jobs",
        json={"title": "Engineer", "company": "Co", "description": "Python, SQL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = job_res.json()["id"]

    ins_res = client.get(f"/api/v1/jobs/{job_id}/match/{resume_id}/insights", headers={"Authorization": f"Bearer {token}"})
    assert ins_res.status_code == status.HTTP_404_NOT_FOUND


def test_match_insights_cross_user_forbidden(client):
    """Test user cannot access insights for another user's job or resume."""
    token1 = get_auth_token(client, email="user.one.ins@example.com", name="User 1")
    token2 = get_auth_token(client, email="user.two.ins@example.com", name="User 2")

    resume1_id = setup_candidate_resume(client, token1)
    resume2_id = setup_candidate_resume(client, token2)

    job1_id = client.post(
        "/api/v1/jobs",
        json={"title": "Job 1", "company": "Co 1", "description": "Python, Docker"},
        headers={"Authorization": f"Bearer {token1}"},
    ).json()["id"]

    # Match User 1's job and resume
    client.post(f"/api/v1/jobs/{job1_id}/match/{resume1_id}", headers={"Authorization": f"Bearer {token1}"})

    # User 2 attempts to get insights for User 1's job/resume -> 404
    bad_res1 = client.get(f"/api/v1/jobs/{job1_id}/match/{resume1_id}/insights", headers={"Authorization": f"Bearer {token2}"})
    assert bad_res1.status_code == status.HTTP_404_NOT_FOUND

    # User 2 attempts with User 1's job and User 2's resume -> 404
    bad_res2 = client.get(f"/api/v1/jobs/{job1_id}/match/{resume2_id}/insights", headers={"Authorization": f"Bearer {token2}"})
    assert bad_res2.status_code == status.HTTP_404_NOT_FOUND
