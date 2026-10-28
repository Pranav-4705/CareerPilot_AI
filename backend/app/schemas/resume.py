from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class ResumeBase(BaseModel):
    original_filename: str


class ResumeUploadResponse(BaseModel):
    id: int
    original_filename: str
    version_number: int = 1
    is_active: bool = True
    uploaded_at: datetime
    status: str = "uploaded"
    message: str = "Resume uploaded successfully"

    model_config = ConfigDict(from_attributes=True)


class ResumeParseResponse(BaseModel):
    id: int
    original_filename: str
    version_number: Optional[int] = None
    is_active: Optional[bool] = None
    status: str = "parsed"
    extracted_text_length: int
    message: str = "Resume parsed and text extracted successfully"

    model_config = ConfigDict(from_attributes=True)


class ResumeHistoryItem(BaseModel):
    id: int
    original_filename: str
    version_number: int
    is_active: bool
    uploaded_at: datetime
    status: str = "uploaded"
    is_parsed: bool = False
    has_analysis: bool = False
    has_ats_score: bool = False
    ats_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    file_path: str
    version_number: int = 1
    is_active: bool = True
    extracted_text: Optional[str] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
