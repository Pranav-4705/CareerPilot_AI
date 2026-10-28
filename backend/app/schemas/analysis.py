from datetime import datetime
from typing import List, Any, Optional
from pydantic import BaseModel, ConfigDict


class ResumeAnalysisResponse(BaseModel):
    id: int
    resume_id: int
    extracted_skills: List[str] = []
    education: List[Any] = []
    experience: List[Any] = []
    projects: List[Any] = []
    certifications: List[Any] = []
    created_at: datetime
    message: str = "Resume structured analysis completed successfully"

    model_config = ConfigDict(from_attributes=True)
