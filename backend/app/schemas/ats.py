from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict


class ComponentScores(BaseModel):
    section_structure: float
    skills_coverage: float
    keyword_quality: float
    experience_depth: float
    readability_format: float


class ATSAnalysisResponse(BaseModel):
    id: int
    resume_id: int
    ats_score: float
    component_scores: Dict[str, float]
    strengths: List[str] = []
    weaknesses: List[str] = []
    missing_skills: List[str] = []
    recommendations: List[str] = []
    created_at: datetime
    message: str = "ATS analysis completed successfully"

    model_config = ConfigDict(from_attributes=True)
