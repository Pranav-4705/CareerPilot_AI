from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Engine configuration
# Note: pool_pre_ping=True tests connections before using them to prevent stale connections
engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency helper to retrieve a database session per request.
    Ensures connection is closed automatically after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
