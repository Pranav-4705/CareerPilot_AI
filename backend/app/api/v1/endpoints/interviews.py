from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.interview import VoiceInterviewTokenResponse
from app.services.livekit_service import create_voice_interview_connection

router = APIRouter()


@router.post(
    "/voice/token",
    response_model=VoiceInterviewTokenResponse,
    summary="Create a LiveKit voice interview session",
)
def create_voice_interview_token(
    current_user: User = Depends(get_current_user),
) -> VoiceInterviewTokenResponse:
    """
    Returns a LiveKit room token for the authenticated candidate.

    The frontend should connect with livekit-client using `url` + `token`.
    The interviewer agent is dispatched into the same room.
    """
    return VoiceInterviewTokenResponse(
        **create_voice_interview_connection(
            user_id=current_user.id,
            user_name=current_user.name,
        )
    )
