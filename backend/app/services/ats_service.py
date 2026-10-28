import re
from typing import Dict, List, Any, Tuple
from app.models.resume_analysis import ResumeAnalysis

# Scoring Component Weights (Sum = 1.0)
WEIGHT_SECTION_STRUCTURE = 0.25   # 25%
WEIGHT_SKILLS_COVERAGE = 0.25      # 25%
WEIGHT_KEYWORD_QUALITY = 0.20     # 20%
WEIGHT_EXPERIENCE_DEPTH = 0.20    # 20%
WEIGHT_READABILITY_FORMAT = 0.10  # 10%

# High-Demand Baseline Tech Skills for Gap Analysis
BASELINE_CORE_SKILLS = [
    "Python",
    "JavaScript",
    "TypeScript",
    "SQL",
    "PostgreSQL",
    "FastAPI",
    "React",
    "Docker",
    "Git",
    "AWS",
    "CI/CD",
    "Linux",
    "REST API",
]

# Action Verbs commonly favored by ATS and technical hiring managers
ACTION_VERBS = {
    "architected", "developed", "engineered", "spearheaded", "optimized",
    "designed", "implemented", "deployed", "managed", "built", "led",
    "improved", "accelerated", "scaled", "automated", "created",
    "established", "orchestrated", "refactored", "integrated",
}

# Regex for detecting quantifiable metrics (percentages, numbers, metric units, team scale)
METRIC_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?%\b|"
    r"\b\d+k\b|"
    r"\$\d+(?:,\d+)*(?:\.\d+)?[kmb]?\b|"
    r"\b\d+\s*(?:\+|-\s*\d+)?\s*(?:users|clients|requests|req/min|req/sec|ms|seconds|minutes|hours|days|engineers|team members|projects|million|billion|gb|tb)\b|"
    r"\b(?:increased|decreased|reduced|improved|boosted|grew)\s+by\s+\d+)",
    re.IGNORECASE,
)


def evaluate_section_structure(
    analysis: ResumeAnalysis,
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Evaluates section completeness and organization.
    Returns (score_0_to_100, strengths, weaknesses, recommendations).
    """
    score = 0.0
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []

    has_skills = bool(analysis.extracted_skills and len(analysis.extracted_skills) > 0)
    has_experience = bool(analysis.experience and len(analysis.experience) > 0)
    has_education = bool(analysis.education and len(analysis.education) > 0)
    has_projects = bool(analysis.projects and len(analysis.projects) > 0)
    has_certifications = bool(analysis.certifications and len(analysis.certifications) > 0)

    # 1. Skills Section (25 pts)
    if has_skills:
        score += 25.0
        strengths.append("Dedicated technical skills section detected.")
    else:
        weaknesses.append("Missing dedicated technical skills section.")
        recommendations.append("Add a dedicated Skills section to help ATS filters index your competencies.")

    # 2. Experience Section (30 pts)
    if has_experience:
        score += 30.0
        strengths.append("Structured work experience section present.")
    else:
        weaknesses.append("Missing work experience section.")
        recommendations.append("Include a detailed Work Experience section highlighting your professional history.")

    # 3. Education Section (25 pts)
    if has_education:
        score += 25.0
        strengths.append("Academic background and education section verified.")
    else:
        weaknesses.append("Missing formal education section.")
        recommendations.append("Add an Education section specifying your degree, institution, and graduation year.")

    # 4. Projects or Certifications (20 pts)
    if has_projects and has_certifications:
        score += 20.0
        strengths.append("Both technical projects and certifications sections are present.")
    elif has_projects or has_certifications:
        score += 15.0
        if has_projects:
            strengths.append("Technical projects section included to showcase practical experience.")
        else:
            strengths.append("Professional certifications section included.")
    else:
        weaknesses.append("Neither technical projects nor certifications were detected.")
        recommendations.append("Add a Projects or Certifications section to provide evidence of practical engineering skills.")

    return min(100.0, score), strengths, weaknesses, recommendations


def evaluate_skills_coverage(
    extracted_skills: List[str],
) -> Tuple[float, List[str], List[str], List[str], List[str]]:
    """
    Evaluates technical skills density, variety, and baseline gap coverage.
    Returns (score_0_to_100, strengths, weaknesses, recommendations, missing_skills).
    """
    count = len(extracted_skills)
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []

    # Calculate skill score based on count
    if count >= 12:
        score = 100.0
        strengths.append(f"Comprehensive skill set with {count} recognized technical competencies.")
    elif count >= 8:
        score = 85.0
        strengths.append(f"Strong skill portfolio with {count} recognized competencies.")
    elif count >= 5:
        score = 70.0
    elif count >= 3:
        score = 50.0
        weaknesses.append("Low density of recognized technical skills.")
        recommendations.append("Expand your skills list with specific frameworks, databases, and DevOps tools you have worked with.")
    elif count >= 1:
        score = 30.0
        weaknesses.append("Minimal technical skills detected.")
        recommendations.append("Add a comprehensive list of programming languages, tools, and platforms.")
    else:
        score = 0.0
        weaknesses.append("No recognized technical skills found.")
        recommendations.append("List your primary programming languages, frameworks, databases, and cloud tools.")

    # Identify missing baseline skills
    current_skills_lower = {s.lower() for s in extracted_skills}
    missing_skills = [
        skill for skill in BASELINE_CORE_SKILLS
        if skill.lower() not in current_skills_lower
    ]

    if missing_skills and count < 8:
        top_missing = missing_skills[:4]
        recommendations.append(
            f"Consider adding in-demand industry competencies if applicable: {', '.join(top_missing)}."
        )

    return score, strengths, weaknesses, recommendations, missing_skills


def evaluate_keyword_quality(
    raw_text: str,
    experience_items: List[Dict[str, Any]],
    project_items: List[Dict[str, Any]],
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Evaluates action verbs and quantifiable metric impact.
    Returns (score_0_to_100, strengths, weaknesses, recommendations).
    """
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []

    combined_text = raw_text.lower()

    # 1. Action Verbs analysis (50 pts max)
    found_verbs = [verb for verb in ACTION_VERBS if re.search(r"\b" + verb + r"\b", combined_text)]
    verb_count = len(found_verbs)

    if verb_count >= 8:
        verb_score = 50.0
        strengths.append(f"Excellent use of {verb_count} distinct action verbs throughout accomplishments.")
    elif verb_count >= 5:
        verb_score = 40.0
        strengths.append("Good variety of action verbs in experience statements.")
    elif verb_count >= 2:
        verb_score = 25.0
    else:
        verb_score = 10.0
        weaknesses.append("Few strong action verbs in job descriptions.")
        recommendations.append("Begin accomplishment bullets with strong action verbs (e.g., 'Architected', 'Spearheaded', 'Optimized', 'Deployed').")

    # 2. Quantifiable Metrics analysis (50 pts max)
    metrics_matches = METRIC_PATTERN.findall(raw_text)
    metric_count = len(metrics_matches)

    if metric_count >= 4:
        metric_score = 50.0
        strengths.append(f"High quantifiable impact with {metric_count} measurable outcome metrics.")
    elif metric_count >= 2:
        metric_score = 35.0
        strengths.append("Includes quantifiable metrics to demonstrate real-world impact.")
    elif metric_count >= 1:
        metric_score = 20.0
        weaknesses.append("Limited quantifiable impact metrics.")
        recommendations.append("Add more specific performance metrics, percentage gains, or scale numbers to quantify achievements.")
    else:
        metric_score = 0.0
        weaknesses.append("No measurable metrics or quantifiable results found.")
        recommendations.append("Quantify your project outcomes (e.g., 'Improved latency by 40%', 'Supported 50k DAU', 'Automated 12 CI pipelines').")

    total_score = min(100.0, verb_score + metric_score)
    return total_score, strengths, weaknesses, recommendations


def evaluate_experience_depth(
    experience_items: List[Dict[str, Any]],
    project_items: List[Dict[str, Any]],
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Evaluates depth of experience bullets and descriptions.
    Returns (score_0_to_100, strengths, weaknesses, recommendations).
    """
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []

    exp_count = len(experience_items)
    proj_count = len(project_items)

    # Experience item count (50 pts max)
    if exp_count >= 2:
        count_score = 50.0
    elif exp_count == 1:
        count_score = 35.0
    else:
        count_score = 0.0

    # Detail lines check (50 pts max)
    total_details = sum(len(item.get("details", [])) for item in experience_items)
    avg_details = (total_details / exp_count) if exp_count > 0 else 0

    if avg_details >= 3:
        detail_score = 50.0
        strengths.append("In-depth descriptions with thorough bullet points per role.")
    elif avg_details >= 1.5:
        detail_score = 35.0
    elif exp_count > 0:
        detail_score = 20.0
        weaknesses.append("Sparse bullet points for work experience roles.")
        recommendations.append("Aim for 3-5 descriptive bullet points for each professional role detailing your specific contributions.")
    else:
        detail_score = 0.0

    # If no work experience but strong projects, award project compensation
    if exp_count == 0 and proj_count >= 2:
        count_score = 35.0
        detail_score = 35.0
        strengths.append("Compensates for limited work experience with well-documented technical projects.")

    total_score = min(100.0, count_score + detail_score)
    return total_score, strengths, weaknesses, recommendations


def evaluate_readability_format(
    raw_text: str,
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Evaluates word count density, length, and readability.
    Returns (score_0_to_100, strengths, weaknesses, recommendations).
    """
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []

    words = raw_text.split()
    word_count = len(words)

    if 300 <= word_count <= 950:
        score = 100.0
        strengths.append(f"Optimal resume length and information density ({word_count} words).")
    elif 200 <= word_count < 300:
        score = 80.0
    elif 950 < word_count <= 1300:
        score = 75.0
        weaknesses.append(f"Resume is slightly verbose ({word_count} words).")
        recommendations.append("Consider condensing older experience to maintain a concise 1-2 page document.")
    elif word_count < 200:
        score = 40.0
        weaknesses.append(f"Resume is significantly brief ({word_count} words).")
        recommendations.append("Flesh out your role descriptions, achievements, and technical stack details.")
    else:
        score = 50.0
        weaknesses.append(f"Resume is excessively long ({word_count} words).")
        recommendations.append("Trim redundant content to keep your resume tightly focused on key achievements.")

    return score, strengths, weaknesses, recommendations


def calculate_ats_analysis(
    analysis: ResumeAnalysis,
    raw_text: str,
) -> Dict[str, Any]:
    """
    Master ATS evaluation pipeline:
    Aggregates scores across all 5 weighted components and compiles
    transparent strengths, weaknesses, missing skills, and recommendations.
    """
    # 1. Structure Score (25%)
    struct_score, struct_str, struct_weak, struct_rec = evaluate_section_structure(analysis)

    # 2. Skills Coverage Score (25%)
    skills_score, skills_str, skills_weak, skills_rec, missing_skills = evaluate_skills_coverage(
        analysis.extracted_skills or []
    )

    # 3. Keyword Quality Score (20%)
    kw_score, kw_str, kw_weak, kw_rec = evaluate_keyword_quality(
        raw_text,
        analysis.experience or [],
        analysis.projects or [],
    )

    # 4. Experience Depth Score (20%)
    exp_score, exp_str, exp_weak, exp_rec = evaluate_experience_depth(
        analysis.experience or [],
        analysis.projects or [],
    )

    # 5. Readability & Formatting Score (10%)
    read_score, read_str, read_weak, read_rec = evaluate_readability_format(raw_text)

    # Weighted Composite Score
    composite = (
        (struct_score * WEIGHT_SECTION_STRUCTURE) +
        (skills_score * WEIGHT_SKILLS_COVERAGE) +
        (kw_score * WEIGHT_KEYWORD_QUALITY) +
        (exp_score * WEIGHT_EXPERIENCE_DEPTH) +
        (read_score * WEIGHT_READABILITY_FORMAT)
    )
    final_score = round(max(0.0, min(100.0, composite)), 1)

    component_scores = {
        "section_structure": round(struct_score, 1),
        "skills_coverage": round(skills_score, 1),
        "keyword_quality": round(kw_score, 1),
        "experience_depth": round(exp_score, 1),
        "readability_format": round(read_score, 1),
    }

    all_strengths = struct_str + skills_str + kw_str + exp_str + read_str
    all_weaknesses = struct_weak + skills_weak + kw_weak + exp_weak + read_weak
    all_recommendations = struct_rec + skills_rec + kw_rec + exp_rec + read_rec

    return {
        "ats_score": final_score,
        "component_scores": component_scores,
        "strengths": all_strengths,
        "weaknesses": all_weaknesses,
        "missing_skills": missing_skills,
        "recommendations": all_recommendations,
    }
