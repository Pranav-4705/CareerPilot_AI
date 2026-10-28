from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, resumes, jobs, interviews

api_router = APIRouter()
api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Job Descriptions & Matching"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Voice Interview"])
