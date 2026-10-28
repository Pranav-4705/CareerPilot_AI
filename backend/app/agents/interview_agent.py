from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_DIR / ".env", override=True)

from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    StopResponse,
    TurnHandlingOptions,
    function_tool,
    inference,
)
from livekit.agents.llm import ChatContext, ChatMessage

from app.agents.interview_state import InterviewState, build_instructions
from app.core.config import settings

logger = logging.getLogger("careerpilot.interview")

AGENT_NAME = settings.LIVEKIT_AGENT_NAME


class TechnicalInterviewer(Agent):
    def __init__(self, *, state: InterviewState, job_ctx: JobContext) -> None:
        self._state = state
        self._job_ctx = job_ctx
        super().__init__(instructions=build_instructions(state))

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=(
                "Greet the candidate in one short sentence, then ask the first "
                "technical primary question. Call record_question after you ask it."
            )
        )

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        text = (new_message.text_content or "").strip()
        if not text:
            raise StopResponse()
        if self._state.completed:
            raise StopResponse()
        if self._state.current_question:
            self._state.last_answer_text = text

    @function_tool
    async def record_question(self, context: RunContext, question: str, topic: str) -> str:
        """Call immediately after asking a new primary interview question."""
        result = self._state.record_question(question, topic)
        await self.update_instructions(build_instructions(self._state))
        return result

    @function_tool
    async def record_answer(self, context: RunContext, answer: str = "") -> str:
        """Call after the candidate finishes answering the current primary question."""
        result = self._state.record_answer(answer or None)
        await self.update_instructions(build_instructions(self._state))
        return result

    @function_tool
    async def complete_interview(self, context: RunContext) -> str:
        """Call after a brief spoken closing when the interview is finished."""
        self._state.completed = True
        await self.update_instructions(build_instructions(self._state))
        asyncio.create_task(self._shutdown_after_close())
        return "Interview complete. Speak a brief goodbye and do not ask anything else."

    async def _shutdown_after_close(self) -> None:
        await asyncio.sleep(6)
        logger.info("Ending LiveKit interview job after closing remarks")
        self._job_ctx.shutdown(reason="interview_complete")


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def interview_session(ctx: JobContext) -> None:
    state = InterviewState()
    session = AgentSession(
        stt=inference.STT(model=settings.LIVEKIT_STT_MODEL, language="en"),
        llm=inference.LLM(model=settings.LIVEKIT_LLM_MODEL),
        tts=inference.TTS(
            model=settings.LIVEKIT_TTS_MODEL,
            voice=settings.LIVEKIT_TTS_VOICE,
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            endpointing={"mode": "fixed", "min_delay": 0.7, "max_delay": 3.5},
            interruption={"mode": "adaptive", "min_duration": 0.5},
            preemptive_generation={"enabled": False},
        ),
    )
    await session.start(
        room=ctx.room,
        agent=TechnicalInterviewer(state=state, job_ctx=ctx),
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
