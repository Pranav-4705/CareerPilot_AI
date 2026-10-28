from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.init_db import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.on_event("startup")
def on_startup():
    init_db()

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Direct health endpoint at /api/health as requested
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "success",
        "message": "CareerPilot AI Backend is operational",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
    }

# Also root /health for convenience
@app.get("/health", tags=["Health"])
def root_health_check():
    return {
        "status": "success",
        "message": "CareerPilot AI Backend is operational",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
    }

# Include API Router for future modular endpoints (e.g., /api/v1/...)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "health": "/api/health",
    }
