from datetime import timedelta
from fastapi import status
from app.core.security import create_access_token, verify_password
from app.models.user import User


def test_user_registration(client, db_session):
    """Test successful user registration."""
    payload = {
        "name": "Jane Candidate",
        "email": "jane.candidate@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Jane Candidate"
    assert data["email"] == "jane.candidate@example.com"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify password is saved as a bcrypt hash in DB
    user_in_db = db_session.query(User).filter(User.email == "jane.candidate@example.com").first()
    assert user_in_db is not None
    assert user_in_db.hashed_password != "SecurePassword123!"
    assert verify_password("SecurePassword123!", user_in_db.hashed_password)


def test_duplicate_user_registration(client):
    """Test that registering with an existing email returns 400."""
    payload = {
        "name": "Original User",
        "email": "duplicate@example.com",
        "password": "InitialPassword123!",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == status.HTTP_201_CREATED

    # Attempt second registration with same email
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in res2.json()["detail"].lower()


def test_login_success(client):
    """Test successful user login with valid credentials."""
    reg_payload = {
        "name": "Login User",
        "email": "login.user@example.com",
        "password": "CorrectPassword123!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "login.user@example.com",
        "password": "CorrectPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_invalid_password(client):
    """Test login with wrong password returns 401."""
    reg_payload = {
        "name": "Auth User",
        "email": "auth.user@example.com",
        "password": "CorrectPassword123!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "auth.user@example.com",
        "password": "WrongPassword!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid email or password" in response.json()["detail"].lower()


def test_login_nonexistent_email(client):
    """Test login with nonexistent email returns 401."""
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "AnyPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid email or password" in response.json()["detail"].lower()


def test_get_me_authenticated(client):
    """Test retrieving authenticated profile with valid token."""
    reg_payload = {
        "name": "Profile Owner",
        "email": "owner@example.com",
        "password": "Password123!",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == "Profile Owner"
    assert data["email"] == "owner@example.com"


def test_get_me_missing_token(client):
    """Test accessing /me without token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "credentials" in response.json()["detail"].lower()


def test_get_me_invalid_token(client):
    """Test accessing /me with malformed token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally-invalid-tampered-token"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_expired_token(client):
    """Test accessing /me with expired token returns 401 and specific expiration error."""
    expired_token = create_access_token(
        subject="999",
        expires_delta=timedelta(hours=-1),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in response.json()["detail"].lower()


def test_complete_frontend_auth_lifecycle(client):
    """
    Simulates the entire frontend auth sequence:
    Register -> Login -> Fetch /me (Dashboard) -> Refresh /me (Session reload) -> Logout -> Unauthenticated access denied
    """
    # 1. Register
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Full Lifecycle User",
            "email": "lifecycle.user@example.com",
            "password": "LifecyclePassword123!",
        },
    )
    assert reg_response.status_code == status.HTTP_201_CREATED

    # 2. Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "lifecycle.user@example.com",
            "password": "LifecyclePassword123!",
        },
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]
    assert token

    # 3. Access Dashboard /me
    dash_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dash_response.status_code == status.HTTP_200_OK
    assert dash_response.json()["name"] == "Full Lifecycle User"

    # 4. Page Refresh (re-fetching /me with stored token)
    refresh_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert refresh_response.status_code == status.HTTP_200_OK
    assert refresh_response.json()["email"] == "lifecycle.user@example.com"

    # 5. Logout simulation (client removes token, calls protected endpoint without Authorization)
    post_logout_response = client.get("/api/v1/auth/me")
    assert post_logout_response.status_code == status.HTTP_401_UNAUTHORIZED
