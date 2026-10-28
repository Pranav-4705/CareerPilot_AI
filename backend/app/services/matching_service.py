import re
from typing import Dict, List, Any, Set
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.models.job_description import JobDescription
from app.models.job_match import JobMatch
from app.services.extractor_service import extract_skills
from app.services.embedding_service import compute_semantic_similarity

# Common English stop words to ignore when calculating keyword gaps
STOP_WORDS: Set[str] = {
    "the", "and", "or", "to", "in", "for", "with", "a", "an", "as", "at", "by",
    "from", "of", "on", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "you", "your", "we",
    "our", "they", "their", "this", "that", "these", "those", "which", "who",
    "whom", "what", "where", "when", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "about",
    "after", "before", "between", "into", "through", "during", "above",
    "below", "under", "again", "further", "then", "once", "here", "there",
    "candidate", "role", "job", "position", "company", "requirements", "qualifications",
    "looking", "seeking", "join", "team", "work", "experience", "years", "skills",
}


def extract_keyword_gaps(job_text: str, resume_text: str, max_gaps: int = 6) -> List[str]:
    """
    Finds prominent technical / domain keywords present in the job description
    that are absent from the candidate's resume.
    """
    job_words = re.findall(r"\b[a-zA-Z]{3,}\b", job_text.lower())
    resume_text_lower = resume_text.lower()

    freq_map: Dict[str, int] = {}
    for word in job_words:
        if word not in STOP_WORDS:
            freq_map[word] = freq_map.get(word, 0) + 1

    sorted_keywords = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)

    gaps: List[str] = []
    for word, _ in sorted_keywords:
        if not re.search(r"\b" + re.escape(word) + r"\b", resume_text_lower):
            gaps.append(word)
            if len(gaps) >= max_gaps:
                break

    return gaps


def calculate_experience_match_score(
    required_experience: Any,
    candidate_experience: List[Any],
    resume_text: str,
) -> tuple[float, bool]:
    """
    Calculates deterministic experience match score (0-100) and match flag.
    """
    req_signals: List[str] = []
    if isinstance(required_experience, dict):
        req_signals = required_experience.get("signals", [])
    elif isinstance(required_experience, list):
        req_signals = required_experience

    # If job has no specific experience requirement, score based on candidate having structured experience
    if not req_signals:
        if candidate_experience and len(candidate_experience) > 0:
            return 100.0, True
        return 75.0, True

    # Extract required years
    req_years = 0
    for sig in req_signals:
        match = re.search(r"(\d+)\+?\s*years?", sig, re.IGNORECASE)
        if match:
            y = int(match.group(1))
            if y > req_years:
                req_years = y

    # If candidate has structured experience entries
    cand_roles_count = len(candidate_experience or [])
    if cand_roles_count >= max(1, req_years // 2):
        score = 100.0 if cand_roles_count >= req_years else max(60.0, (cand_roles_count / max(1, req_years)) * 100.0)
        return min(100.0, score), True
    elif cand_roles_count > 0:
        return 70.0, True
    elif "experience" in resume_text.lower():
        return 50.0, False
    else:
        return 20.0, False


def calculate_education_match_score(
    required_education: List[str],
    candidate_education: List[Any],
    resume_text: str,
) -> tuple[float, bool]:
    """
    Calculates deterministic education match score (0-100) and match flag.
    """
    if not required_education:
        if candidate_education and len(candidate_education) > 0:
            return 100.0, True
        return 80.0, True

    # Check if candidate education matches required keywords (e.g. bachelor, master, cs)
    resume_text_lower = resume_text.lower()
    edu_text = " ".join([str(e) for e in candidate_education]).lower() + " " + resume_text_lower

    matched_count = 0
    for req in required_education:
        words = [w.lower() for w in req.split() if len(w) > 3 and w.lower() not in STOP_WORDS]
        if any(w in edu_text for w in words):
            matched_count += 1

    if matched_count >= len(required_education):
        return 100.0, True
    elif matched_count > 0:
        return 75.0, True
    elif candidate_education and len(candidate_education) > 0:
        return 60.0, False
    else:
        return 30.0, False


def calculate_responsibility_match_score(
    responsibilities: List[str],
    resume_text: str,
    analysis: ResumeAnalysis,
) -> float:
    """
    Calculates deterministic responsibility and keyword alignment score (0-100).
    """
    if not responsibilities:
        return 80.0

    resume_text_lower = resume_text.lower()
    matched_resp = 0

    for resp in responsibilities:
        # Extract meaningful terms from responsibility
        terms = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", resp) if w.lower() not in STOP_WORDS]
        if not terms:
            continue
        term_matches = sum(1 for t in terms if t in resume_text_lower)
        if term_matches >= max(1, len(terms) // 3):
            matched_resp += 1

    score = (matched_resp / max(1, len(responsibilities))) * 100.0
    return min(100.0, max(20.0, score))


def generate_matching_recommendations(
    missing_skills: List[str],
    keyword_gaps: List[str],
    component_scores: Dict[str, float],
) -> List[str]:
    """
    Generates actionable, deterministic recommendations based on detected gaps.
    """
    recommendations: List[str] = []

    if missing_skills:
        top_skills = missing_skills[:5]
        recommendations.append(
            f"Add target role skills to your resume if you have relevant experience: {', '.join(top_skills)}."
        )

    if keyword_gaps:
        top_kw = keyword_gaps[:4]
        recommendations.append(
            f"Incorporate missing domain terms into your experience bullet points: {', '.join(top_kw)}."
        )

    if component_scores.get("experience_match", 100.0) < 70.0:
        recommendations.append(
            "Emphasize your professional roles and quantifiable project accomplishments to meet target experience depth."
        )

    if component_scores.get("responsibility_match", 100.0) < 60.0:
        recommendations.append(
            "Tailor your bullet points using action verbs that directly reflect the core job responsibilities."
        )

    if not recommendations:
        recommendations.append("Strong candidate alignment! Fine-tune bullet points with metrics for maximum impact.")

    return recommendations


def perform_resume_job_match(
    resume: Resume,
    analysis: ResumeAnalysis,
    job: JobDescription,
) -> Dict[str, Any]:
    """
    Performs full 4-component weighted resume-job matching:
    1. Skills Match (50%)
    2. Experience Match (20%)
    3. Education Match (10%)
    4. Responsibility / Keyword Alignment (20%)
    """
    job_full_text = f"{job.title or ''}\n{job.company or ''}\n{job.description or ''}"
    resume_full_text = resume.extracted_text or ""

    # 1. Skills Matching (50% weight)
    if job.extracted_skills:
        job_skills = job.extracted_skills
    else:
        job_skills = extract_skills(job_full_text)
    resume_skills = analysis.extracted_skills or []
    resume_skills_set = {s.lower() for s in resume_skills}

    matched_skills = [s for s in job_skills if s.lower() in resume_skills_set]
    missing_skills = [s for s in job_skills if s.lower() not in resume_skills_set]

    if job_skills:
        skills_score = (len(matched_skills) / len(job_skills)) * 100.0
    else:
        skills_score = 100.0 if len(resume_skills) > 0 else 70.0

    # 2. Experience Matching (20% weight)
    cand_exp = analysis.experience or []
    exp_score, exp_matched = calculate_experience_match_score(
        required_experience=job.required_experience,
        candidate_experience=cand_exp,
        resume_text=resume_full_text,
    )

    # 3. Education Matching (10% weight)
    cand_edu = analysis.education or []
    edu_score, edu_matched = calculate_education_match_score(
        required_education=job.education_requirements or [],
        candidate_education=cand_edu,
        resume_text=resume_full_text,
    )

    # 4. Responsibility & Keyword Alignment (20% weight)
    resp_score = calculate_responsibility_match_score(
        responsibilities=job.responsibilities or [],
        resume_text=resume_full_text,
        analysis=analysis,
    )

    # Keyword Gaps
    keyword_gaps = extract_keyword_gaps(job_full_text, resume_full_text)

    # 5. Combined Weighted Score
    overall_match_score = (
        (skills_score * 0.50) +
        (exp_score * 0.20) +
        (edu_score * 0.10) +
        (resp_score * 0.20)
    )
    final_score = round(max(0.0, min(100.0, overall_match_score)), 1)

    component_scores = {
        "skills_match": round(skills_score, 1),
        "experience_match": round(exp_score, 1),
        "education_match": round(edu_score, 1),
        "responsibility_match": round(resp_score, 1),
    }

    recommendations = generate_matching_recommendations(
        missing_skills=missing_skills,
        keyword_gaps=keyword_gaps,
        component_scores=component_scores,
    )

    return {
        "match_score": final_score,
        "component_scores": component_scores,
        "skill_match_score": round(skills_score, 1),
        "semantic_similarity_score": round(resp_score, 1),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "keyword_gaps": keyword_gaps,
        "experience_match": exp_matched,
        "education_match": edu_matched,
        "recommendations": recommendations,
    }
