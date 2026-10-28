from pathlib import Path
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings for CareerPilot AI Backend.
    All values are configurable via environment variables or a .env file.
    """
    PROJECT_NAME: str = "CareerPilot AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & JWT Configuration
    SECRET_KEY: str = "development_secret_key_change_in_production_1234567890_careerpilot"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # File Upload Configuration
    UPLOAD_DIR: str = "uploads/resumes"
    MAX_UPLOAD_SIZE_MB: int = 5  # 5 MB max resume upload size

    # Semantic Embedding Model Configuration
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # Google Gemini API Configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OpenRouter API Configuration
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "openrouter/free"

    # --- AI Provider Selection -------------------------------------------------
    # Chooses which provider backs app.services.ai_service.AIService:
    #   ollama -> local Ollama first, Gemini/OpenRouter as an optional fallback
    #   gemini -> Gemini/OpenRouter first
    #   none   -> no provider at all (deterministic fallbacks only)
    AI_PROVIDER: str = "ollama"

    # Local Ollama provider: no API key, prompts never leave this machine.
    # OLLAMA_MODEL is empty by default on purpose - a model must be pulled
    # first (`ollama pull llama3.2:3b`) before Ollama can answer anything.
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = ""
    OLLAMA_TIMEOUT_SECONDS: int = 120
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_MAX_TOKENS: int = 2048

    # --- LiveKit voice interview ----------------------------------------------
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    LIVEKIT_AGENT_NAME: str = "careerpilot-interviewer"
    LIVEKIT_STT_MODEL: str = "assemblyai/universal-3-5-pro"
    LIVEKIT_LLM_MODEL: str = "google/gemini-3.8-flash"
    LIVEKIT_TTS_MODEL: str = "fishaudio/s2.1-pro"
    LIVEKIT_TTS_VOICE: str = "fa4c9eb3dccc4806b382b40d61c6b10a"

    # --- Database --------------------------------------------------------------
    POSTGRES_USER: str = "careerpilot_user"
    POSTGRES_PASSWORD: str = "careerpilot_password"
    POSTGRES_DB: str = "careerpilot_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_SERVER: str = "localhost"

    # Full SQLAlchemy URL. When empty it is assembled from the POSTGRES_* parts
    # above. Set it to switch engines without touching code, e.g.
    #   DATABASE_URL=sqlite:///./careerpilot.db
    DATABASE_URL: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def sync_database_url(self) -> str:
        """
        SQLAlchemy URL for the synchronous engine.

        An explicit DATABASE_URL wins. Otherwise PostgreSQL is built from the
        POSTGRES_* parts, which is what docker-compose provides.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str], None]) -> List[str]:
        """Accepts a JSON array or a comma-separated string from the environment."""
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        text = str(v).strip()
        if text.startswith("["):
            import json

            return json.loads(text)
        return [origin.strip() for origin in text.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parents[2] / ".env"),
            ".env",
        ),
        extra="ignore",
    )


settings = Settings()