from app.models.user import User
from app.models.resume import Resume
from app.models.job_description import JobDescription
from app.models.job_match import JobMatch
from app.core.security import get_password_hash


def test_job_description_model_persistence_and_relationships(db_session):
    """Test creating, persisting, and querying JobDescription with JSON fields and relationships."""
    # 1. Create User
    user = User(
        name="Job Model Candidate",
        email="jobmodel.user@example.com",
        hashed_password=get_password_hash("SecretPassword123!"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Create JobDescription with structured JSON fields
    job = JobDescription(
        user_id=user.id,
        title="Staff Backend Engineer",
        company="TechCorp Inc.",
        description="Looking for an experienced backend engineer proficient in Python and distributed systems.",
        extracted_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        extracted_keywords=["distributed systems", "microservices", "scale", "latency"],
        required_experience={"min_years": 5, "seniority": "Staff"},
        education_requirements=["B.S. in Computer Science or equivalent"],
        responsibilities=[
            "Design and architect high-throughput microservices",
            "Lead database performance optimization initiatives",
        ],
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 3. Verify fields
    assert job.id is not None
    assert job.user_id == user.id
    assert job.title == "Staff Backend Engineer"
    assert job.company == "TechCorp Inc."
    assert "Python" in job.extracted_skills
    assert "microservices" in job.extracted_keywords
    assert job.required_experience["min_years"] == 5
    assert len(job.education_requirements) == 1
    assert len(job.responsibilities) == 2
    assert job.created_at is not None
    assert job.updated_at is not None

    # 4. Verify User -> JobDescription relationship
    assert len(user.job_descriptions) == 1
    assert user.job_descriptions[0].id == job.id
    assert job.user.email == "jobmodel.user@example.com"


def test_job_match_model_persistence_and_relationships(db_session):
    """Test creating and persisting JobMatch referencing User, Resume, and JobDescription."""
    # 1. Create User
    user = User(
        name="Matcher User",
        email="matcher.user@example.com",
        hashed_password=get_password_hash("SecretPassword123!"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Create Resume
    resume = Resume(
        user_id=user.id,
        original_filename="matcher_cv.pdf",
        file_path="uploads/resumes/matcher_cv.pdf",
        extracted_text="Experienced Python Developer",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    # 3. Create JobDescription
    job = JobDescription(
        user_id=user.id,
        title="Python Engineer",
        company="Global Software",
        description="Python, PostgreSQL, AWS required",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 4. Create JobMatch record
    match = JobMatch(
        user_id=user.id,
        resume_id=resume.id,
        job_description_id=job.id,
        match_score=85.5,
        matched_skills=["Python", "PostgreSQL"],
        missing_skills=["AWS"],
        matched_keywords=["developer", "software"],
        missing_keywords=["cloud", "architecture"],
        requirement_gaps=["Missing 2 years AWS experience"],
        recommendations=["Highlight AWS deployment experience in projects."],
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)

    # 5. Verify fields and relationships
    assert match.id is not None
    assert match.user_id == user.id
    assert match.resume_id == resume.id
    assert match.job_description_id == job.id
    assert match.match_score == 85.5
    assert "Python" in match.matched_skills
    assert "AWS" in match.missing_skills
    assert "architecture" in match.missing_keywords
    assert len(match.requirement_gaps) == 1
    assert len(match.recommendations) == 1
    assert match.created_at is not None

    # Relationship verifications
    assert match.user.id == user.id
    assert match.resume.id == resume.id
    assert match.job_description.id == job.id
    assert len(user.job_matches) == 1
    assert len(job.job_matches) == 1
    assert len(resume.job_matches) == 1


def test_multiple_job_matches_for_same_resume_and_job(db_session):
    """Test that multiple analyses / JobMatch historical records can exist for the same resume and job."""
    user = User(
        name="Multi Matcher",
        email="multimatcher@example.com",
        hashed_password=get_password_hash("Password123!"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    resume = Resume(
        user_id=user.id,
        original_filename="cv_v1.pdf",
        file_path="uploads/resumes/cv_v1.pdf",
    )
    job = JobDescription(
        user_id=user.id,
        title="Full Stack Developer",
        description="React and Python",
    )
    db_session.add_all([resume, job])
    db_session.commit()
    db_session.refresh(resume)
    db_session.refresh(job)

    # First match run (e.g. initial score 70)
    match1 = JobMatch(
        user_id=user.id,
        resume_id=resume.id,
        job_description_id=job.id,
        match_score=70.0,
        matched_skills=["Python"],
        missing_skills=["React"],
    )
    # Second match run (e.g. re-evaluated score 85)
    match2 = JobMatch(
        user_id=user.id,
        resume_id=resume.id,
        job_description_id=job.id,
        match_score=85.0,
        matched_skills=["Python", "React"],
        missing_skills=[],
    )

    db_session.add_all([match1, match2])
    db_session.commit()
    db_session.refresh(match1)
    db_session.refresh(match2)

    assert match1.id != match2.id
    assert match1.resume_id == match2.resume_id == resume.id
    assert match1.job_description_id == match2.job_description_id == job.id
    assert len(job.job_matches) == 2
    assert len(resume.job_matches) == 2
