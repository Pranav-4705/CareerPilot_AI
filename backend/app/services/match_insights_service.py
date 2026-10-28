import re
from typing import Dict, List, Any, Optional
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.models.job_description import JobDescription
from app.models.job_match import JobMatch
from app.services.matching_service import STOP_WORDS


def categorize_missing_skill_priority(skill: str, job_text: str) -> str:
    """
    Deterministically categorizes missing skill priority based on job text context.
    - 'high': explicitly under required/qualifications or repeated 2+ times
    - 'medium': mentioned in body or responsibilities
    - 'low': supporting mention
    """
    skill_lower = skill.lower()
    job_lower = job_text.lower()

    # Count occurrences
    occurrences = len(re.findall(r"\b" + re.escape(skill_lower) + r"\b", job_lower))

    # Check if in a 'requirements' or 'qualifications' or 'must have' line
    in_required_block = False
    for line in job_lower.split("\n"):
        if skill_lower in line:
            if any(k in line for k in ["require", "must", "qualification", "essential", "core", "proficien", "experience in"]):
                in_required_block = True
                break

    if in_required_block or occurrences >= 2:
        return "high"
    elif occurrences == 1:
        return "medium"
    return "low"


def generate_match_insights(
    job: JobDescription,
    resume: Resume,
    analysis: ResumeAnalysis,
    job_match: JobMatch,
) -> Dict[str, Any]:
    """
    Computes deterministic match insights, prioritized skill gaps,
    experience/education alignment signals, and actionable recommendations.
    """
    job_full_text = f"{job.title or ''}\n{job.company or ''}\n{job.description or ''}"
    resume_full_text = resume.extracted_text or ""
    resume_lower = resume_full_text.lower()

    # -------------------------------------------------------------
    # 1. Skill Gap Analysis
    # -------------------------------------------------------------
    job_skills = job.extracted_skills or []
    matched_skills = job_match.matched_skills or []
    missing_skills = job_match.missing_skills or []

    if job_skills:
        skill_match_pct = round((len(matched_skills) / len(job_skills)) * 100.0, 1)
        skill_explanation = None
    else:
        skill_match_pct = 0.0
        skill_explanation = "No explicit technical skill requirements were detected in the target job description."

    prioritized_missing = []
    for skill in missing_skills:
        pri = categorize_missing_skill_priority(skill, job_full_text)
        prioritized_missing.append({"name": skill, "priority": pri})

    skill_gap = {
        "match_percentage": skill_match_pct,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "prioritized_missing_skills": prioritized_missing,
        "explanation": skill_explanation,
    }

    # -------------------------------------------------------------
    # 2. Experience Gap Insights
    # -------------------------------------------------------------
    req_exp = job.required_experience or {}
    exp_signals = []
    if isinstance(req_exp, dict):
        exp_signals = req_exp.get("signals", [])
    elif isinstance(req_exp, list):
        exp_signals = req_exp

    cand_roles = analysis.experience or []

    if not exp_signals:
        exp_status = "not_specified"
        exp_req_text = "No explicit duration specified in posting"
        exp_msg = "The job posting does not list a mandatory years-of-experience threshold."
    else:
        exp_req_text = ", ".join(exp_signals[:2])
        # Detect required years
        req_years = 0
        for sig in exp_signals:
            m = re.search(r"(\d+)\+?\s*years?", sig, re.IGNORECASE)
            if m:
                y = int(m.group(1))
                if y > req_years:
                    req_years = y

        if req_years > 0:
            if len(cand_roles) >= req_years:
                exp_status = "meets"
                exp_msg = f"Candidate profile demonstrates {len(cand_roles)} documented career roles satisfying the {req_years}+ years target."
            elif len(cand_roles) > 0:
                exp_status = "meets" if len(cand_roles) >= max(1, req_years // 2) else "does_not_meet"
                exp_msg = f"Job targets {req_years}+ years. Candidate profile shows {len(cand_roles)} documented career role(s)."
            else:
                exp_status = "unknown"
                exp_msg = "The resume does not provide enough explicit role timeline information to verify this duration."
        else:
            if len(cand_roles) > 0:
                exp_status = "meets"
                exp_msg = "Candidate shows documented industry experience matching role criteria."
            else:
                exp_status = "unknown"
                exp_msg = "Experience requirement could not be reliably determined from the resume."

    experience_insight = {
        "status": exp_status,
        "requirement": exp_req_text,
        "message": exp_msg,
    }

    # -------------------------------------------------------------
    # 3. Education Gap Insights
    # -------------------------------------------------------------
    edu_reqs = job.education_requirements or []
    cand_edu = analysis.education or []

    if not edu_reqs:
        edu_status = "not_specified"
        edu_req_text = "No specific academic degree stated"
        edu_msg = "The job posting does not list a mandatory educational degree requirement."
    else:
        edu_req_text = ", ".join(edu_reqs[:2])
        # Compare candidate education keywords
        cand_edu_text = " ".join([str(e) for e in cand_edu]).lower() + " " + resume_lower
        matched_edu = False
        for req in edu_reqs:
            words = [w.lower() for w in req.split() if len(w) > 3 and w.lower() not in STOP_WORDS]
            if any(w in cand_edu_text for w in words):
                matched_edu = True
                break

        if matched_edu:
            edu_status = "meets"
            edu_msg = "Detected candidate academic background fulfills the stated educational requirements."
        elif cand_edu and len(cand_edu) > 0:
            edu_status = "unknown"
            edu_msg = "Candidate has documented higher education, but specific degree field equivalence needs manual review."
        else:
            edu_status = "unknown"
            edu_msg = "Your education section does not clearly demonstrate the academic qualification requested by this role."

    education_insight = {
        "status": edu_status,
        "requirement": edu_req_text,
        "message": edu_msg,
    }

    # -------------------------------------------------------------
    # 4. Responsibility Alignment Insights
    # -------------------------------------------------------------
    responsibilities = job.responsibilities or []
    aligned_areas: List[str] = []
    improvement_areas: List[str] = []

    if not responsibilities:
        alignment_score = 80.0
    else:
        for resp in responsibilities:
            terms = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", resp) if w.lower() not in STOP_WORDS]
            if not terms:
                continue
            term_matches = sum(1 for t in terms if t in resume_lower)
            if term_matches >= max(1, len(terms) // 3):
                aligned_areas.append(resp)
            else:
                improvement_areas.append(resp)

        alignment_score = round((len(aligned_areas) / max(1, len(responsibilities))) * 100.0, 1)

    responsibility_insight = {
        "alignment_score": alignment_score,
        "aligned_areas": aligned_areas[:5],
        "improvement_areas": improvement_areas[:5],
    }

    # -------------------------------------------------------------
    # 5. Candidate Strengths for this Role
    # -------------------------------------------------------------
    strengths: List[str] = []
    if skill_match_pct >= 70.0:
        strengths.append(f"Strong technical skill coverage ({len(matched_skills)} matching technologies).")
    elif len(matched_skills) > 0:
        strengths.append(f"Core technical capability matches: {', '.join(matched_skills[:3])}.")

    if exp_status == "meets":
        strengths.append("Career background demonstrates compatible experience depth for this seniority level.")

    if edu_status == "meets":
        strengths.append("Academic qualifications directly satisfy role prerequisites.")

    if alignment_score >= 60.0 and aligned_areas:
        strengths.append(f"Demonstrated project alignment with key role responsibilities.")

    if not strengths:
        strengths.append("Foundational technical competencies detected for cross-functional role transition.")

    # -------------------------------------------------------------
    # 6. Actionable Improvement Recommendations with Severity
    # -------------------------------------------------------------
    recommendations: List[Dict[str, str]] = []

    # High priority missing skills
    high_pri_skills = [s["name"] for s in prioritized_missing if s["priority"] == "high"]
    if high_pri_skills:
        recommendations.append({
            "severity": "critical" if len(high_pri_skills) >= 3 else "high",
            "message": f"Consider highlighting practical experience with core target skills if applicable: {', '.join(high_pri_skills[:4])}.",
        })

    # Medium/Low priority missing skills
    other_missing = [s["name"] for s in prioritized_missing if s["priority"] in ["medium", "low"]]
    if other_missing and not high_pri_skills:
        recommendations.append({
            "severity": "medium",
            "message": f"Consider developing or demonstrating proficiency in supporting technologies: {', '.join(other_missing[:4])}.",
        })

    # Experience gap
    if exp_status == "does_not_meet":
        recommendations.append({
            "severity": "high",
            "message": f"Job description requests {exp_req_text}. Highlight full career milestones and leadership projects to demonstrate required seniority.",
        })
    elif exp_status == "unknown" and exp_signals:
        recommendations.append({
            "severity": "medium",
            "message": "Clarify role timelines, dates, and tenures in your work experience section to clearly evidence your seniority.",
        })

    # Responsibility gap
    if improvement_areas and alignment_score < 60.0:
        top_imp = improvement_areas[0]
        recommendations.append({
            "severity": "medium",
            "message": f"Tailor your project bullet points using action verbs relevant to: \"{top_imp[:70]}...\".",
        })

    # Keyword alignment
    kw_gaps = job_match.keyword_gaps or []
    if kw_gaps:
        recommendations.append({
            "severity": "low",
            "message": f"Incorporate relevant domain terminology into your summary/experience: {', '.join(kw_gaps[:4])}.",
        })

    # Positive info note
    if job_match.match_score >= 75.0:
        recommendations.append({
            "severity": "info",
            "message": "Strong overall candidate compatibility! Review target role requirements during interview preparation.",
        })

    return {
        "job_id": job.id,
        "resume_id": resume.id,
        "match_score": job_match.match_score,
        "strengths": strengths,
        "skill_gap": skill_gap,
        "experience": experience_insight,
        "education": education_insight,
        "responsibilities": responsibility_insight,
        "recommendations": recommendations,
    }
