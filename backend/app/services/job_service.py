import re
from typing import Dict, List, Any
from app.services.extractor_service import extract_skills

# Regex patterns for experience extraction
EXPERIENCE_PATTERNS = [
    re.compile(r"(\b\d+\+?\s*(?:-\s*\d+)?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+[\w\s]{0,40})?(?:experience|exp)?)", re.IGNORECASE),
    re.compile(r"((?:minimum|at least|over)\s+\d+\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+[\w\s]{0,40})?(?:experience|exp)?)", re.IGNORECASE),
]

# Regex patterns for education extraction
EDUCATION_PATTERNS = [
    re.compile(r"((?:bachelor'?s?|master'?s?|ph\.?d\.?|doctorate|b\.?tech|b\.?e\.?|m\.?tech|m\.?s\.?|b\.?s\.?|b\.?sc|m\.?sc|diploma)(?:\s+(?:degree|in|of))?(?:\s+[A-Za-z\s,/-]{0,50})?)", re.IGNORECASE),
    re.compile(r"((?:computer science|information technology|software engineering|data science|related technical field|related field|electrical engineering))", re.IGNORECASE),
]

# Common action verbs indicating responsibilities
RESPONSIBILITY_VERBS = {
    "build", "develop", "design", "maintain", "create", "implement", "lead", "manage",
    "collaborate", "architect", "deploy", "optimize", "deliver", "scale", "troubleshoot",
    "write", "ensure", "participate", "work", "conduct", "integrate", "support", "drive",
}


def normalize_job_text(text: str) -> str:
    """
    Normalizes job description text:
    - Normalizes line endings to \n
    - Removes excessive vertical and horizontal whitespace
    - Preserves meaningful paragraph and line structure
    - Strips leading/trailing whitespace
    """
    if not text or not text.strip():
        return ""

    # Normalize line breaks
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean per line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]

    # Remove repeated blank lines (allow at most 1 empty line between blocks)
    cleaned_lines: List[str] = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned_lines.append("")
                prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    return "\n".join(cleaned_lines).strip()


def extract_experience_requirements(text: str) -> List[str]:
    """
    Deterministically detects explicit experience requirements from job description text.
    """
    results: List[str] = []
    seen: set = set()

    for line in text.split("\n"):
        clean_line = line.strip(" -*•\t")
        for pat in EXPERIENCE_PATTERNS:
            matches = pat.findall(clean_line)
            for m in matches:
                m_clean = m.strip()
                if len(m_clean) > 3 and m_clean.lower() not in seen:
                    seen.add(m_clean.lower())
                    # If line is short and specific, use whole line; otherwise use the match
                    if len(clean_line) <= 80 and any(w in clean_line.lower() for w in ["year", "yr", "exp"]):
                        results.append(clean_line)
                    else:
                        results.append(m_clean)

    # Deduplicate while preserving order
    deduped: List[str] = []
    for r in results:
        if r not in deduped:
            deduped.append(r)

    return deduped


def extract_education_requirements(text: str) -> List[str]:
    """
    Deterministically detects explicit education qualifications from job description text.
    """
    results: List[str] = []
    seen: set = set()

    for line in text.split("\n"):
        clean_line = line.strip(" -*•\t")
        for pat in EDUCATION_PATTERNS:
            matches = pat.findall(clean_line)
            for m in matches:
                m_clean = m.strip()
                if len(m_clean) > 3 and m_clean.lower() not in seen:
                    seen.add(m_clean.lower())
                    if len(clean_line) <= 90 and any(w in clean_line.lower() for w in ["degree", "bachelor", "master", "tech", "science", "field"]):
                        results.append(clean_line)
                    else:
                        results.append(m_clean)

    deduped: List[str] = []
    for r in results:
        if r not in deduped:
            deduped.append(r)

    return deduped


def extract_responsibilities(text: str) -> List[str]:
    """
    Deterministically extracts key responsibility statements from job description.
    """
    responsibilities: List[str] = []
    in_resp_section = False

    for line in text.split("\n"):
        clean = line.strip(" -*•\t")
        if not clean:
            continue

        lower = clean.lower()
        # Section header check
        if any(h in lower for h in ["responsibilities", "what you'll do", "what you will do", "duties", "the role", "key tasks"]):
            in_resp_section = True
            continue

        if in_resp_section and any(h in lower for h in ["requirements", "qualifications", "what we're looking for", "skills", "benefits", "about you"]):
            in_resp_section = False
            continue

        first_word = clean.split()[0].lower().rstrip("s") if clean.split() else ""
        is_bullet = line.strip().startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5."))

        if (in_resp_section and (is_bullet or len(clean) > 15)) or (first_word in RESPONSIBILITY_VERBS and is_bullet):
            if len(clean) > 10 and clean not in responsibilities:
                responsibilities.append(clean)

    return responsibilities[:10]


def extract_job_keywords(text: str, max_keywords: int = 12) -> List[str]:
    """
    Extracts prominent technical and domain keywords from job text.
    """
    words = re.findall(r"\b[A-Za-z]{3,}\b", text)
    from app.services.matching_service import STOP_WORDS

    freq: Dict[str, int] = {}
    for w in words:
        wl = w.lower()
        if wl not in STOP_WORDS and len(wl) > 2:
            freq[w] = freq.get(w, 0) + 1

    sorted_kws = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in sorted_kws[:max_keywords]]


def analyze_job_description_text(title: str, company: str, description: str) -> Dict[str, Any]:
    """
    Runs full deterministic structured extraction pipeline on a job description.
    """
    combined_text = f"{title or ''}\n{company or ''}\n{description or ''}"
    norm_desc = normalize_job_text(description or "")

    skills = extract_skills(combined_text)
    experience = extract_experience_requirements(norm_desc)
    education = extract_education_requirements(norm_desc)
    responsibilities = extract_responsibilities(norm_desc)
    keywords = extract_job_keywords(norm_desc)

    return {
        "extracted_skills": skills,
        "extracted_keywords": keywords,
        "required_experience": {"signals": experience, "count": len(experience)},
        "education_requirements": education,
        "responsibilities": responsibilities,
    }
