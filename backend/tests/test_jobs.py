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


def get_auth_token(client, email="job.matcher@example.com", name="Job Matcher"):
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


def create_sample_resume_pdf() -> bytes:
    """Creates a sample candidate resume PDF."""
    text = """
Alex River
Full Stack Python Engineer | alex@example.com

SKILLS
Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux

WORK EXPERIENCE
Backend Developer at TechSolutions
- Built REST APIs in Python using FastAPI and PostgreSQL.
- Containerized backend services with Docker and deployed to Linux servers.
- Collaborated using Git for version control.

EDUCATION
B.S. in Computer Science, 2020
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def setup_candidate_resume(client, token: str) -> int:
    """Uploads, parses, and structurally analyzes a resume, returning the resume_id."""
    pdf_bytes = create_sample_resume_pdf()
    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("alex_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]
    client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token}"})
    return resume_id


def test_job_description_creation_and_retrieval(client, db_session):
    """Test creating and retrieving a job description."""
    token = get_auth_token(client, email="recruiter.user@example.com")

    payload = {
        "title": "Senior Backend Engineer",
        "company": "NextGen Cloud",
        "description": "Looking for a Senior Backend Engineer proficient in Python, FastAPI, PostgreSQL, and AWS.",
    }

    # 1. Create Job
    create_res = client.post(
        "/api/v1/jobs",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    job_data = create_res.json()
    assert job_data["title"] == "Senior Backend Engineer"
    assert job_data["company"] == "NextGen Cloud"
    assert "id" in job_data
    job_id = job_data["id"]

    # 2. Get Job
    get_res = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["id"] == job_id


def test_job_ownership_security(client):
    """Test that a user cannot view another user's job description."""
    token1 = get_auth_token(client, email="user.one.job@example.com", name="User 1")
    token2 = get_auth_token(client, email="user.two.job@example.com", name="User 2")

    create_res = client.post(
        "/api/v1/jobs",
        json={"title": "Data Engineer", "company": "DataCorp", "description": "Python, SQL, Spark"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    job_id = create_res.json()["id"]

    # User 2 tries to access User 1's job
    get_res = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


def test_resume_to_job_matching_pipeline(client, db_session):
    """Test full resume-to-job matching, skill overlap, missing skills, semantic score, and DB persistence."""
    token = get_auth_token(client, email="matching.full@example.com")
    resume_id = setup_candidate_resume(client, token)

    # Create target job requiring some matching and some missing skills
    job_payload = {
        "title": "Backend Systems Engineer",
        "company": "Cloud Innovators",
        "description": """
We are seeking a Backend Systems Engineer to join our team.
Required Qualifications:
- Strong experience with Python, FastAPI, and PostgreSQL.
- Hands-on expertise with Docker, Git, and Linux.
- Experience with AWS, Kubernetes, and GraphQL is a huge plus.
Responsibilities:
- Build high-scale microservices and database architectures.
- Collaborate with cross-functional engineering teams.
""",
    }
    job_res = client.post("/api/v1/jobs", json=job_payload, headers={"Authorization": f"Bearer {token}"})
    job_id = job_res.json()["id"]

    # Perform Match
    match_res = client.post(
        f"/api/v1/jobs/{job_id}/match/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert match_res.status_code == status.HTTP_200_OK
    data = match_res.json()

    # Score bounds checks
    assert 0.0 <= data["match_score"] <= 100.0
    assert 0.0 <= data["skill_match_score"] <= 100.0
    assert 0.0 <= data["semantic_similarity_score"] <= 100.0

    # Skill matching checks
    matched = data["matched_skills"]
    missing = data["missing_skills"]

    assert "Python" in matched
    assert "FastAPI" in matched
    assert "PostgreSQL" in matched
    assert "Docker" in matched

    # Missing skills detection
    assert "AWS" in missing or "Kubernetes" in missing or "GraphQL" in missing

    # Recommendations and keyword gaps
    assert len(data["recommendations"]) >= 1
    assert "missing_skills" in str(data["recommendations"]).lower() or "add" in str(data["recommendations"]).lower()

    # Verify DB Persistence in JobMatch table
    db_match = db_session.query(JobMatch).filter(
        JobMatch.resume_id == resume_id,
        JobMatch.job_description_id == job_id,
    ).first()
    assert db_match is not None
    assert db_match.match_score == data["match_score"]
    assert "Python" in db_match.matched_skills


def test_cross_user_matching_forbidden(client):
    """Test that a candidate cannot match using another user's resume or job."""
    token1 = get_auth_token(client, email="user.first@example.com", name="First")
    token2 = get_auth_token(client, email="user.second@example.com", name="Second")

    resume1_id = setup_candidate_resume(client, token1)
    resume2_id = setup_candidate_resume(client, token2)

    job1_res = client.post(
        "/api/v1/jobs",
        json={"title": "Dev 1", "company": "Co 1", "description": "Python developer"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    job1_id = job1_res.json()["id"]

    # User 2 attempts to match User 1's job with User 2's resume -> 404
    match_att1 = client.post(
        f"/api/v1/jobs/{job1_id}/match/{resume2_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert match_att1.status_code == status.HTTP_404_NOT_FOUND

    # User 1 attempts to match User 1's job with User 2's resume -> 404
    match_att2 = client.post(
        f"/api/v1/jobs/{job1_id}/match/{resume2_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert match_att2.status_code == status.HTTP_404_NOT_FOUND


def test_matching_with_nonexistent_ids(client):
    """Test matching with nonexistent job_id or resume_id returns 404."""
    token = get_auth_token(client, email="nonexistent.tester@example.com")
    resume_id = setup_candidate_resume(client, token)

    # Nonexistent job
    res1 = client.post(
        f"/api/v1/jobs/99999/match/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == status.HTTP_404_NOT_FOUND

    # Nonexistent resume
    job_res = client.post(
        "/api/v1/jobs",
        json={"title": "Role", "company": "Co", "description": "Python"},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = job_res.json()["id"]

    res2 = client.post(
        f"/api/v1/jobs/{job_id}/match/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == status.HTTP_404_NOT_FOUND


def test_matching_unauthorized(client):
    """Test calling endpoints without authentication header returns 401."""
    res = client.post(
        "/api/v1/jobs",
        json={"title": "Test", "company": "Test Co", "description": "Test"},
    )
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
