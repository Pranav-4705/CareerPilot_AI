from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    extracted_skills = Column(JSON, nullable=True, default=list)
    extracted_keywords = Column(JSON, nullable=True, default=list)
    required_experience = Column(JSON, nullable=True, default=dict)
    education_requirements = Column(JSON, nullable=True, default=list)
    responsibilities = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="job_descriptions")
    job_matches = relationship(
        "JobMatch",
        back_populates="job_description",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JobDescription(id={self.id}, user_id={self.user_id}, title='{self.title}', company='{self.company}')>"
