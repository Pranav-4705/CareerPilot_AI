from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    description: str = Field(..., min_length=5)


class JobDescriptionCreate(JobDescriptionBase):
    pass


class JobDescriptionResponse(JobDescriptionBase):
    id: int
    user_id: Optional[int] = None
    extracted_skills: Optional[List[str]] = []
    extracted_keywords: Optional[List[str]] = []
    required_experience: Optional[Dict[str, Any]] = {}
    education_requirements: Optional[List[str]] = []
    responsibilities: Optional[List[str]] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobAnalyzeResponse(BaseModel):
    id: int
    job_id: int
    required_skills: List[str] = []
    experience_requirements: List[str] = []
    education_requirements: List[str] = []
    responsibilities: List[str] = []
    extracted_keywords: List[str] = []
    message: str = "Job description analysis completed successfully"

    model_config = ConfigDict(from_attributes=True)
