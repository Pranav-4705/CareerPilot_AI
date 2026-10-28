from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any], tags=["Health"])
def get_health_status() -> Dict[str, Any]:
    """
    Health check endpoint to verify backend service status.
    """
    return {
        "status": "success",
        "message": "CareerPilot AI Backend is healthy",
        "service": "careerpilot-api",
        "version": "1.0.0",
    }
