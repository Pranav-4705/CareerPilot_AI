import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Use SQLite in-memory database with StaticPool for fast, isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def hermetic_ai_provider():
    """
    Pins the AI provider for the whole test session.

    Tests must never depend on whatever the developer happens to run locally
    (e.g. a live Ollama server on 127.0.0.1:11434), so provider selection is
    forced onto the Gemini adapter here. Tests that assert provider selection
    or exercise Ollama set `settings.AI_PROVIDER` themselves via monkeypatch,
    and mock the HTTP layer, so they stay fully offline.
    """
    original = settings.AI_PROVIDER
    settings.AI_PROVIDER = "gemini"
    yield
    settings.AI_PROVIDER = original


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
