import logging
from app.core.database import engine, Base
# Import all models so Base.metadata knows about them
import app.models # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Creates all database tables defined in SQLAlchemy models.
    Suitable for local development and initial schema setup.
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully.")
        logger.info(f"Registered tables: {list(Base.metadata.tables.keys())}")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise e


if __name__ == "__main__":
    init_db()
