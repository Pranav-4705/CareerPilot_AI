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


def get_auth_token(client, email="matcher.phase6@example.com", name="Matcher User"):
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


def create_sample_resume_pdf(skills: str = "Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux", exp_roles: int = 2) -> bytes:
    """Creates a sample candidate resume PDF."""
    roles_text = "\n".join([
        f"Software Engineer at Company {i}\n- Developed backend services with Python and PostgreSQL.\n- Deployed containers using Docker."
        for i in range(1, exp_roles + 1)
    ])
    text = f"""
Jordan Rivers
Senior Full Stack Engineer | jordan@example.com

SKILLS
{skills}

WORK EXPERIENCE
{roles_text}

EDUCATION
Bachelor of Science in Computer Science, 2020
"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def setup_candidate_resume(client, token: str, skills: str = "Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux", parsed: bool = True, analyzed: bool = True) -> int:
    """Uploads, and conditionally parses and analyzes a resume."""
    pdf_bytes = create_sample_resume_pdf(skills=skills)
    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("jordan_cv.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    resume_id = up_res.json()["id"]
    if parsed:
        client.post(f"/api/v1/resumes/{resume_id}/parse", headers={"Authorization": f"Bearer {token}"})
    if analyzed:
        client.post(f"/api/v1/resumes/{resume_id}/analyze", headers={"Authorization": f"Bearer {token}"})
    return resume_id


def test_job_creation_and_listing(client):
    """Test job creation, validation, and user-scoped listing."""
    token = get_auth_token(client, email="create.job@example.com")

    # Empty description fails with 400 or 422
    bad_res = client.post(
        "/api/v1/jobs",
        json={"title": "Dev", "company": "Co", "description": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_res.status_code in [status.HTTP_400_BAD_REQUEST, 422]

    # Valid creation
    create_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend Python Developer",
            "company": "ScaleTech",
            "description": "We are seeking a Backend Developer with 3+ years of experience in Python, FastAPI, and PostgreSQL. Bachelor's degree in Computer Science required.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    job_id = create_res.json()["id"]

    # List jobs
    list_res = client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == status.HTTP_200_OK
    jobs = list_res.json()
    assert len(jobs) >= 1
    assert jobs[0]["id"] == job_id
    assert jobs[0]["title"] == "Backend Python Developer"


def test_job_structured_analysis_extraction(client):
    """Test POST /api/v1/jobs/{job_id}/analyze extracts skills, experience, education, and responsibilities."""
    token = get_auth_token(client, email="analyze.job@example.com")

    job_text = """
We are looking for a Senior Cloud Backend Engineer.

Responsibilities:
- Build and maintain high-scale backend services using Python and FastAPI.
- Design database schemas in PostgreSQL and MySQL.
- Deploy containerized microservices with Docker and Kubernetes on AWS.

Requirements:
- 3+ years of professional backend development experience.
- Bachelor's degree in Computer Science or related field.
- Strong proficiency in Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL, and Git.
"""
    create_res = client.post(
        "/api/v1/jobs",
        json={"title": "Senior Cloud Backend Engineer", "company": "CloudWorks", "description": job_text},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = create_res.json()["id"]

    # Analyze Job
    analyze_res = client.post(f"/api/v1/jobs/{job_id}/analyze", headers={"Authorization": f"Bearer {token}"})
    assert analyze_res.status_code == status.HTTP_200_OK
    data = analyze_res.json()

    # Skills check
    assert "Python" in data["required_skills"]
    assert "FastAPI" in data["required_skills"]
    assert "Docker" in data["required_skills"]
    assert "Kubernetes" in data["required_skills"]
    assert "AWS" in data["required_skills"]

    # Experience check
    assert len(data["experience_requirements"]) >= 1
    assert any("3" in str(e) for e in data["experience_requirements"])

    # Education check
    assert len(data["education_requirements"]) >= 1
    assert any("computer science" in str(ed).lower() or "bachelor" in str(ed).lower() for ed in data["education_requirements"])

    # Responsibilities check
    assert len(data["responsibilities"]) >= 1


def test_deterministic_resume_to_job_matching_and_scoring(client, db_session):
    """Test 4-component deterministic matching with skill overlap, missing skills, and bounds."""
    token = get_auth_token(client, email="match.deterministic@example.com")
    resume_id = setup_candidate_resume(client, token, skills="Python, FastAPI, PostgreSQL, Docker, Git")

    job_text = """
Backend Developer
Requirements:
- 2+ years of experience with Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS.
- Bachelor's degree in Computer Science.
Responsibilities:
- Build and maintain REST APIs and microservices.
"""
    job_res = client.post(
        "/api/v1/jobs",
        json={"title": "Backend Developer", "company": "TechInc", "description": job_text},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = job_res.json()["id"]

    # Match
    match_res = client.post(f"/api/v1/jobs/{job_id}/match/{resume_id}", headers={"Authorization": f"Bearer {token}"})
    assert match_res.status_code == status.HTTP_200_OK
    res_data = match_res.json()

    # Verify transparent component breakdown
    assert "component_scores" in res_data
    comp = res_data["component_scores"]
    assert "skills_match" in comp
    assert "experience_match" in comp
    assert "education_match" in comp
    assert "responsibility_match" in comp

    # Check bounds
    assert 0.0 <= res_data["match_score"] <= 100.0
    assert 0.0 <= comp["skills_match"] <= 100.0
    assert 0.0 <= comp["experience_match"] <= 100.0
    assert 0.0 <= comp["education_match"] <= 100.0
    assert 0.0 <= comp["responsibility_match"] <= 100.0

    # Skills overlap
    assert "Python" in res_data["matched_skills"]
    assert "FastAPI" in res_data["matched_skills"]
    assert "PostgreSQL" in res_data["matched_skills"]
    assert "Docker" in res_data["matched_skills"]

    # Missing skills (Kubernetes, AWS)
    assert "Kubernetes" in res_data["missing_skills"] or "AWS" in res_data["missing_skills"]


def test_matching_unparsed_or_unanalyzed_resume_rejected(client):
    """Test matching an unparsed or unanalyzed resume returns 400."""
    token = get_auth_token(client, email="unparsed.match@example.com")

    # 1. Unparsed resume
    unparsed_id = setup_candidate_resume(client, token, parsed=False, analyzed=False)
    job_res = client.post(
        "/api/v1/jobs",
        json={"title": "Engineer", "company": "Co", "description": "Python, SQL, 2 years exp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    job_id = job_res.json()["id"]

    res1 = client.post(f"/api/v1/jobs/{job_id}/match/{unparsed_id}", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Parsed but unanalyzed resume
    parsed_only_id = setup_candidate_resume(client, token, parsed=True, analyzed=False)
    res2 = client.post(f"/api/v1/jobs/{job_id}/match/{parsed_only_id}", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == status.HTTP_400_BAD_REQUEST


def test_cross_user_job_and_matching_isolation(client):
    """Test that User A and User B cannot access or match each other's jobs or resumes."""
    token_a = get_auth_token(client, email="user.a.sec@example.com", name="User A")
    token_b = get_auth_token(client, email="user.b.sec@example.com", name="User B")

    resume_a = setup_candidate_resume(client, token_a)
    resume_b = setup_candidate_resume(client, token_b)

    job_a = client.post(
        "/api/v1/jobs",
        json={"title": "Role A", "company": "Co A", "description": "Python, FastAPI"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["id"]

    # User B attempts to access User A's job -> 404
    assert client.get(f"/api/v1/jobs/{job_a}", headers={"Authorization": f"Bearer {token_b}"}).status_code == status.HTTP_404_NOT_FOUND

    # User B attempts to analyze User A's job -> 404
    assert client.post(f"/api/v1/jobs/{job_a}/analyze", headers={"Authorization": f"Bearer {token_b}"}).status_code == status.HTTP_404_NOT_FOUND

    # User B attempts to match User A's job with User B's resume -> 404
    assert client.post(f"/api/v1/jobs/{job_a}/match/{resume_b}", headers={"Authorization": f"Bearer {token_b}"}).status_code == status.HTTP_404_NOT_FOUND

    # User A attempts to match User A's job with User B's resume -> 404
    assert client.post(f"/api/v1/jobs/{job_a}/match/{resume_b}", headers={"Authorization": f"Bearer {token_a}"}).status_code == status.HTTP_404_NOT_FOUND
