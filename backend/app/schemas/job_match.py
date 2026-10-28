from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict


class JobMatchBase(BaseModel):
    resume_id: int
    job_description_id: int


class JobMatchResponse(JobMatchBase):
    id: int
    user_id: Optional[int] = None
    match_score: float
    component_scores: Optional[Dict[str, float]] = None
    matched_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []
    matched_keywords: Optional[List[str]] = []
    missing_keywords: Optional[List[str]] = []
    keyword_gaps: Optional[List[str]] = []
    requirement_gaps: Optional[List[str]] = []
    experience_match: Optional[bool] = None
    education_match: Optional[bool] = None
    recommendations: Optional[List[str]] = []
    skill_match_score: Optional[float] = None
    semantic_similarity_score: Optional[float] = None
    created_at: datetime
    message: Optional[str] = "Resume and job matched successfully"

    model_config = ConfigDict(from_attributes=True)
