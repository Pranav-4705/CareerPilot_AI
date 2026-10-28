import re
from typing import Dict, List, Any, Optional

# Standardized Skills Taxonomy (Canonical Name -> Regex pattern)
SKILLS_TAXONOMY: Dict[str, str] = {
    # Programming Languages
    "Python": r"\bpython\b",
    "JavaScript": r"\b(?:javascript|js)\b",
    "TypeScript": r"\b(?:typescript|ts)\b",
    "Java": r"\bjava\b(?!script)",
    "C++": r"\bc\+\+\b",
    "C#": r"\bc#\b",
    "C": r"\bc\b(?![\+\#\w])",
    "Go": r"\b(?:golang|go)\b",
    "Rust": r"\brust\b",
    "Ruby": r"\bruby\b",
    "PHP": r"\bphp\b",
    "SQL": r"\bsql\b",
    "HTML": r"\bhtml5?\b",
    "CSS": r"\bcss3?\b",
    "Bash": r"\b(?:bash|shell\s+scripting)\b",
    "Kotlin": r"\bkotlin\b",
    "Swift": r"\bswift\b",
    "R": r"\br\s+programming|\b(?<![a-zA-Z])R(?![a-zA-Z])\b",
    "Scala": r"\bscala\b",
    # Frameworks & Libraries
    "FastAPI": r"\bfastapi\b",
    "Django": r"\bdjango\b",
    "Flask": r"\bflask\b",
    "React": r"\breact(?:\.js)?\b",
    "Next.js": r"\bnext(?:\.js)?\b",
    "Vue.js": r"\bvue(?:\.js)?\b",
    "Angular": r"\bangular(?:\.js)?\b",
    "Node.js": r"\bnode(?:\.js)?\b",
    "Express.js": r"\bexpress(?:\.js)?\b",
    "Spring Boot": r"\bspring\s+boot\b",
    "Tailwind CSS": r"\btailwind(?:\s+css)?\b",
    "Bootstrap": r"\bbootstrap\b",
    "PyTorch": r"\bpytorch\b",
    "TensorFlow": r"\btensorflow\b",
    "Scikit-learn": r"\bscikit[-_]?learn\b",
    "Pandas": r"\bpandas\b",
    "NumPy": r"\bnumpy\b",
    # Databases & Storage
    "PostgreSQL": r"\b(?:postgresql|postgres)\b",
    "MySQL": r"\bmysql\b",
    "MongoDB": r"\bmongodb\b",
    "Redis": r"\bredis\b",
    "SQLite": r"\bsqlite\b",
    "DynamoDB": r"\bdynamodb\b",
    "Cassandra": r"\bcassandra\b",
    "Elasticsearch": r"\belasticsearch\b",
    # Cloud & DevOps
    "AWS": r"\b(?:aws|amazon\s+web\s+services)\b",
    "Azure": r"\b(?:azure|microsoft\s+azure)\b",
    "GCP": r"\b(?:gcp|google\s+cloud(?:\s+platform)?)\b",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\b(?:kubernetes|k8s)\b",
    "CI/CD": r"\bci[/-]cd\b",
    "Git": r"\bgit\b",
    "GitHub": r"\bgithub\b",
    "GitLab": r"\bgitlab\b",
    "Linux": r"\blinux\b",
    "Terraform": r"\bterraform\b",
    "Ansible": r"\bansible\b",
    "Nginx": r"\bnginx\b",
    # Architecture & Methodology
    "REST API": r"\brest(?:ful)?(?:\s+apis?|\s+web\s+services)?\b",
    "GraphQL": r"\bgraphql\b",
    "Microservices": r"\bmicroservices?\b",
    "Machine Learning": r"\bmachine\s+learning\b",
    "Deep Learning": r"\bdeep\s+learning\b",
    "NLP": r"\b(?:nlp|natural\s+language\s+processing)\b",
    "Computer Vision": r"\bcomputer\s+vision\b",
    "Generative AI": r"\bgenerative\s+ai\b",
    "LLM": r"\b(?:llm|large\s+language\s+models?)\b",
    "Agile": r"\bagile\b",
    "Scrum": r"\bscrum\b",
}

# Section Header Regex Patterns
SECTION_PATTERNS = {
    "skills": re.compile(
        r"^(?:(?:technical|core|key|professional)\s+)?(?:skills|competencies|technologies|tech\s+stack|programming\s+languages|tools(?:\s+and\s+technologies)?)\b",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^(?:(?:work|professional|employment|career|relevant)\s+)?(?:experience|history|employment)\b",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"^(?:education(?:al\s+background)?|academic\s+(?:background|qualifications|history)|degrees?|academics)\b",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(?:(?:personal|academic|key|selected|technical|software)\s+)?projects\b",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"^(?:(?:licenses\s+&?\s+|professional\s+|courses\s+&?\s+)?(?:certifications|certificates|courses|licenses))\b",
        re.IGNORECASE,
    ),
}


def split_resume_into_sections(text: str) -> Dict[str, str]:
    """
    Identifies section headings in resume text and partitions the content
    into normalized section keys ('skills', 'experience', 'education', 'projects', 'certifications').
    """
    lines = text.split("\n")
    sections: Dict[str, List[str]] = {}
    current_section: Optional[str] = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current_section and sections[current_section]:
                sections[current_section].append("")
            continue

        # Clean punctuation from header candidate (e.g., "SKILLS:", "## Education")
        header_candidate = re.sub(r"^[\#\*\-\s]+|[:\-_]+$", "", line).strip()

        # Check if line matches a known section heading
        matched_section = None
        for section_key, pattern in SECTION_PATTERNS.items():
            if pattern.match(header_candidate):
                matched_section = section_key
                break

        if matched_section:
            current_section = matched_section
            if current_section not in sections:
                sections[current_section] = []
        else:
            if current_section:
                sections[current_section].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def extract_skills(text: str, skills_section_text: Optional[str] = None) -> List[str]:
    """
    Extracts and normalizes skills using the taxonomy dictionary.
    Scans the dedicated skills section (with higher confidence) and the full text.
    """
    found_skills: List[str] = []
    seen = set()

    search_target = f"{skills_section_text or ''}\n\n{text}"

    for canonical_name, pattern in SKILLS_TAXONOMY.items():
        if re.search(pattern, search_target, re.IGNORECASE):
            if canonical_name not in seen:
                seen.add(canonical_name)
                found_skills.append(canonical_name)

    return found_skills


def parse_list_items(section_text: str) -> List[Dict[str, Any]]:
    """
    Splits multi-line section text into structured item blocks.
    Preserves exact user text without inventing content.
    """
    if not section_text:
        return []

    # Split by double newline or distinct bullet blocks
    raw_blocks = re.split(r"\n\s*\n+", section_text)
    items: List[Dict[str, Any]] = []

    for block in raw_blocks:
        cleaned_block = block.strip()
        if not cleaned_block:
            continue

        block_lines = [l.strip() for l in cleaned_block.split("\n") if l.strip()]
        if not block_lines:
            continue

        # Primary title/heading is usually the first line
        title = block_lines[0]
        details = block_lines[1:] if len(block_lines) > 1 else []

        items.append({
            "title": title,
            "details": details,
            "raw_text": cleaned_block,
        })

    return items


def extract_structured_resume_data(extracted_text: str) -> Dict[str, Any]:
    """
    Main extraction pipeline:
    Partitions resume into sections and extracts structured JSON for:
    - extracted_skills (List[str])
    - education (List[Dict])
    - experience (List[Dict])
    - projects (List[Dict])
    - certifications (List[Dict])
    """
    if not extracted_text or not extracted_text.strip():
        return {
            "extracted_skills": [],
            "education": [],
            "experience": [],
            "projects": [],
            "certifications": [],
        }

    sections = split_resume_into_sections(extracted_text)

    skills_text = sections.get("skills", "")
    skills = extract_skills(extracted_text, skills_text)

    education = parse_list_items(sections.get("education", ""))
    experience = parse_list_items(sections.get("experience", ""))
    projects = parse_list_items(sections.get("projects", ""))
    certifications = parse_list_items(sections.get("certifications", ""))

    return {
        "extracted_skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
    }
