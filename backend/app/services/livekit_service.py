from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from livekit import api

from app.core.config import settings


def create_voice_interview_connection(*, user_id: int, user_name: str) -> dict[str, str]:
    """Mint a participant token and dispatch the CareerPilot interviewer into the room."""
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET.",
        )

    room_name = f"interview-{user_id}-{uuid.uuid4().hex[:10]}"
    identity = f"candidate-{user_id}"
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(user_name or identity)
        .with_ttl(timedelta(hours=1))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )
    return {
        "url": settings.LIVEKIT_URL,
        "token": token,
        "room_name": room_name,
        "identity": identity,
        "agent_name": settings.LIVEKIT_AGENT_NAME,
    }
