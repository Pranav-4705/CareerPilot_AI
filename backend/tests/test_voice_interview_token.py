from fastapi import status


def test_voice_token_requires_auth(client):
    response = client.post("/api/v1/interviews/voice/token")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_voice_token_requires_livekit_config(client, monkeypatch):
    payload = {
        "name": "Voice Candidate",
        "email": "voice.candidate@example.com",
        "password": "SecurePassword123!",
    }
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == status.HTTP_201_CREATED

    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == status.HTTP_200_OK
    token = login.json()["access_token"]

    from app.core.config import settings

    monkeypatch.setattr(settings, "LIVEKIT_URL", "")
    monkeypatch.setattr(settings, "LIVEKIT_API_KEY", "")
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", "")

    response = client.post(
        "/api/v1/interviews/voice/token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "LiveKit is not configured" in response.json()["detail"]


def test_voice_token_success_when_configured(client):
    payload = {
        "name": "LiveKit Candidate",
        "email": "livekit.candidate@example.com",
        "password": "SecurePassword123!",
    }
    register = client.post("/api/v1/auth/register", json=payload)
    if register.status_code != status.HTTP_201_CREATED:
        assert register.status_code == status.HTTP_400_BAD_REQUEST

    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == status.HTTP_200_OK
    token = login.json()["access_token"]

    response = client.post(
        "/api/v1/interviews/voice/token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "token" in data and len(data["token"]) > 20
    assert data["url"] == "wss://careerpilot-ai-x8yieeln.livekit.cloud"
    assert data["room_name"].startswith("interview-")
    assert data["agent_name"] == "careerpilot-interviewer"
