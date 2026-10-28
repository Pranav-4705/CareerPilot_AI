from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PrioritizedSkill(BaseModel):
    name: str
    priority: str  # "high" | "medium" | "low" | "needs_review"


class SkillGapInsight(BaseModel):
    match_percentage: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    prioritized_missing_skills: List[PrioritizedSkill] = []
    explanation: Optional[str] = None


class ExperienceInsight(BaseModel):
    status: str  # "meets" | "does_not_meet" | "unknown" | "not_specified"
    requirement: Optional[str] = None
    message: str


class EducationInsight(BaseModel):
    status: str  # "meets" | "does_not_meet" | "unknown" | "not_specified"
    requirement: Optional[str] = None
    message: str


class ResponsibilityInsight(BaseModel):
    alignment_score: float
    aligned_areas: List[str] = []
    improvement_areas: List[str] = []


class MatchRecommendation(BaseModel):
    severity: str  # "critical" | "high" | "medium" | "low" | "info"
    message: str


class MatchInsightsResponse(BaseModel):
    job_id: int
    resume_id: int
    match_score: float
    strengths: List[str] = []
    skill_gap: SkillGapInsight
    experience: ExperienceInsight
    education: EducationInsight
    responsibilities: ResponsibilityInsight
    recommendations: List[MatchRecommendation] = []

    model_config = ConfigDict(from_attributes=True)
