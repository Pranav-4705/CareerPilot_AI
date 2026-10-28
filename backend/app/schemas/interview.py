from pydantic import BaseModel


class VoiceInterviewTokenResponse(BaseModel):
    url: str
    token: str
    room_name: str
    identity: str
    agent_name: str
