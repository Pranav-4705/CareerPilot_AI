import os
import io
import fitz
from fastapi import status
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis


def get_auth_token(client, email="version.tester@example.com", name="Version Tester"):
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


def create_pdf_content(title: str, skills: str) -> bytes:
    """Helper to create a PDF with distinct text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\nSKILLS:\n{skills}\n\nEXPERIENCE:\nSoftware Engineer at TechCorp\n- Developed applications.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_resume_version_increment_and_active_status(client, db_session):
    """Test that multiple uploads increment version_number (1, 2, 3) and update is_active."""
    token = get_auth_token(client, email="version.increment@example.com")

    # 1. First upload -> Version 1, Active = True
    res1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_v1.pdf", io.BytesIO(create_pdf_content("Candidate V1", "Python, SQL")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == status.HTTP_201_CREATED
    data1 = res1.json()
    assert data1["version_number"] == 1
    assert data1["is_active"] is True
    id1 = data1["id"]

    # 2. Second upload -> Version 2, Active = True, Version 1 becomes Inactive
    res2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_v2.pdf", io.BytesIO(create_pdf_content("Candidate V2", "Python, FastAPI, Docker")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == status.HTTP_201_CREATED
    data2 = res2.json()
    assert data2["version_number"] == 2
    assert data2["is_active"] is True
    id2 = data2["id"]

    # 3. Third upload -> Version 3, Active = True, Version 2 becomes Inactive
    res3 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_v3.pdf", io.BytesIO(create_pdf_content("Candidate V3", "Python, FastAPI, AWS, Kubernetes")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res3.status_code == status.HTTP_201_CREATED
    data3 = res3.json()
    assert data3["version_number"] == 3
    assert data3["is_active"] is True
    id3 = data3["id"]

    # Verify in DB
    db_v1 = db_session.query(Resume).filter(Resume.id == id1).first()
    db_v2 = db_session.query(Resume).filter(Resume.id == id2).first()
    db_v3 = db_session.query(Resume).filter(Resume.id == id3).first()

    assert db_v1.version_number == 1 and db_v1.is_active is False
    assert db_v2.version_number == 2 and db_v2.is_active is False
    assert db_v3.version_number == 3 and db_v3.is_active is True

    # Previous versions remain accessible via GET /{id}
    get_v1 = client.get(f"/api/v1/resumes/{id1}", headers={"Authorization": f"Bearer {token}"})
    assert get_v1.status_code == status.HTTP_200_OK
    assert get_v1.json()["version_number"] == 1
    assert get_v1.json()["is_active"] is False


def test_resume_history_endpoint(client):
    """Test GET /api/v1/resumes returns user history ordered newest first and isolated per user."""
    token_user_a = get_auth_token(client, email="user.a.hist@example.com", name="User A")
    token_user_b = get_auth_token(client, email="user.b.hist@example.com", name="User B")

    # User A uploads 2 versions
    client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_a1.pdf", io.BytesIO(create_pdf_content("A1", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token_user_a}"},
    )
    client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_a2.pdf", io.BytesIO(create_pdf_content("A2", "FastAPI")), "application/pdf")},
        headers={"Authorization": f"Bearer {token_user_a}"},
    )

    # User B uploads 1 version
    client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume_b1.pdf", io.BytesIO(create_pdf_content("B1", "Java")), "application/pdf")},
        headers={"Authorization": f"Bearer {token_user_b}"},
    )

    # User A checks history
    hist_a_res = client.get("/api/v1/resumes", headers={"Authorization": f"Bearer {token_user_a}"})
    assert hist_a_res.status_code == status.HTTP_200_OK
    hist_a = hist_a_res.json()
    assert len(hist_a) == 2
    # Ordered newest first
    assert hist_a[0]["version_number"] == 2
    assert hist_a[0]["is_active"] is True
    assert hist_a[1]["version_number"] == 1
    assert hist_a[1]["is_active"] is False
    # Does not contain User B's resume
    assert not any("resume_b1" in r["original_filename"] for r in hist_a)

    # User B checks history
    hist_b_res = client.get("/api/v1/resumes", headers={"Authorization": f"Bearer {token_user_b}"})
    assert hist_b_res.status_code == status.HTTP_200_OK
    hist_b = hist_b_res.json()
    assert len(hist_b) == 1
    assert hist_b[0]["version_number"] == 1
    assert "resume_b1" in hist_b[0]["original_filename"]


def test_resume_history_unauthenticated_rejected(client):
    """Test unauthenticated request to /api/v1/resumes is rejected with 401."""
    res = client.get("/api/v1/resumes")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_active_resume_endpoint(client):
    """Test GET /api/v1/resumes/active returns active resume or 404 if none."""
    token = get_auth_token(client, email="active.tester@example.com")

    # 1. No resumes yet -> 404
    no_active_res = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"})
    assert no_active_res.status_code == status.HTTP_404_NOT_FOUND

    # 2. Upload V1 -> Active is V1
    up1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("active_v1.pdf", io.BytesIO(create_pdf_content("Active V1", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id1 = up1.json()["id"]

    act1_res = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"})
    assert act1_res.status_code == status.HTTP_200_OK
    assert act1_res.json()["id"] == id1
    assert act1_res.json()["version_number"] == 1

    # 3. Upload V2 -> Active switches to V2
    up2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("active_v2.pdf", io.BytesIO(create_pdf_content("Active V2", "FastAPI")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id2 = up2.json()["id"]

    act2_res = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"})
    assert act2_res.status_code == status.HTTP_200_OK
    assert act2_res.json()["id"] == id2
    assert act2_res.json()["version_number"] == 2


def test_analysis_independence_between_versions(client, db_session):
    """Test that analyzing version 2 does not alter or overwrite analysis of version 1."""
    token = get_auth_token(client, email="analysis.isolation@example.com")

    # 1. Upload & Analyze Version 1 (Skills: Python, SQL)
    up1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("iso_v1.pdf", io.BytesIO(create_pdf_content("Iso V1", "Python, SQL")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id1 = up1.json()["id"]
    client.post(f"/api/v1/resumes/{id1}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{id1}/analyze", headers={"Authorization": f"Bearer {token}"})
    ats1_res = client.post(f"/api/v1/resumes/{id1}/ats-analyze", headers={"Authorization": f"Bearer {token}"})
    assert ats1_res.status_code == status.HTTP_200_OK
    score1 = ats1_res.json()["ats_score"]

    # 2. Upload & Analyze Version 2 (Skills: Python, FastAPI, Docker, AWS, PostgreSQL, React, TypeScript)
    full_skills_text = "Python, FastAPI, Docker, AWS, PostgreSQL, React, TypeScript, Git, Linux, REST API"
    up2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("iso_v2.pdf", io.BytesIO(create_pdf_content("Iso V2", full_skills_text)), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id2 = up2.json()["id"]
    client.post(f"/api/v1/resumes/{id2}/parse", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/v1/resumes/{id2}/analyze", headers={"Authorization": f"Bearer {token}"})
    ats2_res = client.post(f"/api/v1/resumes/{id2}/ats-analyze", headers={"Authorization": f"Bearer {token}"})
    assert ats2_res.status_code == status.HTTP_200_OK
    score2 = ats2_res.json()["ats_score"]

    # 3. Verify Version 1's analysis record in DB remains completely unchanged
    v1_analysis = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == id1).first()
    v2_analysis = db_session.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == id2).first()

    assert v1_analysis.id != v2_analysis.id
    assert v1_analysis.ats_score == score1
    assert v2_analysis.ats_score == score2
    assert "TypeScript" not in v1_analysis.extracted_skills
    assert "TypeScript" in v2_analysis.extracted_skills


def test_activate_resume_version_and_deactivate_previous(client, db_session):
    """Test activating an earlier version successfully switches active state without modifying analysis."""
    token = get_auth_token(client, email="activate.test@example.com")

    # Upload V1 and V2
    up1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("v1.pdf", io.BytesIO(create_pdf_content("V1", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id1 = up1.json()["id"]

    up2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("v2.pdf", io.BytesIO(create_pdf_content("V2", "FastAPI")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id2 = up2.json()["id"]

    # Currently V2 is active
    assert client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"}).json()["id"] == id2

    # Activate V1
    act_res = client.post(f"/api/v1/resumes/{id1}/activate", headers={"Authorization": f"Bearer {token}"})
    assert act_res.status_code == status.HTTP_200_OK
    assert act_res.json()["id"] == id1
    assert act_res.json()["is_active"] is True

    # Check active endpoint now returns V1
    active_now = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"}).json()
    assert active_now["id"] == id1
    assert active_now["is_active"] is True

    # Check V2 is inactive in DB
    v2_db = db_session.query(Resume).filter(Resume.id == id2).first()
    assert v2_db.is_active is False


def test_cannot_activate_another_users_resume(client):
    """Test candidate cannot activate another candidate's resume."""
    token_a = get_auth_token(client, email="user.a.act@example.com")
    token_b = get_auth_token(client, email="user.b.act@example.com")

    up_a = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("a.pdf", io.BytesIO(create_pdf_content("A", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    id_a = up_a.json()["id"]

    # User B attempts to activate User A's resume
    act_res = client.post(f"/api/v1/resumes/{id_a}/activate", headers={"Authorization": f"Bearer {token_b}"})
    assert act_res.status_code == status.HTTP_404_NOT_FOUND


def test_delete_inactive_resume_preserves_active(client, db_session):
    """Test deleting an inactive resume version removes record and file, active version remains intact."""
    token = get_auth_token(client, email="del.inactive@example.com")

    # Upload V1 (inactive after V2) and V2 (active)
    up1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("del_v1.pdf", io.BytesIO(create_pdf_content("Del V1", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id1 = up1.json()["id"]

    up2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("del_v2.pdf", io.BytesIO(create_pdf_content("Del V2", "FastAPI")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id2 = up2.json()["id"]

    # Delete V1
    del_res = client.delete(f"/api/v1/resumes/{id1}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == status.HTTP_200_OK

    # V1 is gone
    get_v1 = client.get(f"/api/v1/resumes/{id1}", headers={"Authorization": f"Bearer {token}"})
    assert get_v1.status_code == status.HTTP_404_NOT_FOUND

    # V2 is still active
    active = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"}).json()
    assert active["id"] == id2
    assert active["is_active"] is True


def test_delete_active_resume_promotes_newest_remaining(client, db_session):
    """Test deleting active resume version promotes the newest remaining version to active."""
    token = get_auth_token(client, email="del.active@example.com")

    # Upload V1 and V2 (V2 is active)
    up1 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("prom_v1.pdf", io.BytesIO(create_pdf_content("Prom V1", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id1 = up1.json()["id"]

    up2 = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("prom_v2.pdf", io.BytesIO(create_pdf_content("Prom V2", "FastAPI")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id2 = up2.json()["id"]

    # Delete V2 (active)
    del_res = client.delete(f"/api/v1/resumes/{id2}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == status.HTTP_200_OK
    assert del_res.json()["promoted_active_id"] == id1

    # Active resume is now promoted V1
    active = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"}).json()
    assert active["id"] == id1
    assert active["is_active"] is True


def test_delete_only_resume_clears_active_and_history(client):
    """Test deleting user's only resume results in empty history and 404 for active."""
    token = get_auth_token(client, email="del.only@example.com")

    up = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("only.pdf", io.BytesIO(create_pdf_content("Only", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    id_only = up.json()["id"]

    # Delete it
    del_res = client.delete(f"/api/v1/resumes/{id_only}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == status.HTTP_200_OK

    # History is empty
    hist = client.get("/api/v1/resumes", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(hist) == 0

    # Active returns 404
    act = client.get("/api/v1/resumes/active", headers={"Authorization": f"Bearer {token}"})
    assert act.status_code == status.HTTP_404_NOT_FOUND


def test_cannot_delete_another_users_resume(client):
    """Test candidate cannot delete another candidate's resume."""
    token_a = get_auth_token(client, email="user.a.del@example.com")
    token_b = get_auth_token(client, email="user.b.del@example.com")

    up_a = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("a_del.pdf", io.BytesIO(create_pdf_content("A", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    id_a = up_a.json()["id"]

    # User B attempts to delete User A's resume
    del_res = client.delete(f"/api/v1/resumes/{id_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_res.status_code == status.HTTP_404_NOT_FOUND


def test_authorization_cross_user_resume_manipulation(client):
    """Test that User B cannot access, parse, analyze, or ATS-analyze User A's resume."""
    token_a = get_auth_token(client, email="victim.user@example.com", name="Victim A")
    token_b = get_auth_token(client, email="attacker.user@example.com", name="Attacker B")

    # User A uploads and parses
    up_res = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("confidential.pdf", io.BytesIO(create_pdf_content("Secret", "Python")), "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resume_a_id = up_res.json()["id"]

    # User B attempts GET by ID -> 404
    get_res = client.get(f"/api/v1/resumes/{resume_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_res.status_code == status.HTTP_404_NOT_FOUND

    # User B attempts POST /parse -> 404
    parse_res = client.post(f"/api/v1/resumes/{resume_a_id}/parse", headers={"Authorization": f"Bearer {token_b}"})
    assert parse_res.status_code == status.HTTP_404_NOT_FOUND

    # User B attempts POST /analyze -> 404
    analyze_res = client.post(f"/api/v1/resumes/{resume_a_id}/analyze", headers={"Authorization": f"Bearer {token_b}"})
    assert analyze_res.status_code == status.HTTP_404_NOT_FOUND

    # User B attempts POST /ats-analyze -> 404
    ats_res = client.post(f"/api/v1/resumes/{resume_a_id}/ats-analyze", headers={"Authorization": f"Bearer {token_b}"})
    assert ats_res.status_code == status.HTTP_404_NOT_FOUND
