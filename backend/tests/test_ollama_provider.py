"""
Local Ollama provider integration (Phase B).

Every test here is offline: the Ollama HTTP boundary is mocked, so the suite
never requires Ollama to be installed or running. The only test that touches a
real server is `test_real_ollama_generates_technical_and_hr_question`, which is
opt-in via `RUN_OLLAMA_SMOKE=1`.

Coverage: provider selection via AI_PROVIDER, the Ollama transport and its
structured-response parsing (valid / fenced / malformed / empty / errors /
timeouts), deterministic fallback, Technical and HR interviews driven through
`AIService` end to end, Gemini remaining selectable, and the architecture
boundaries that keep provider knowledge out of the engine and strategies.
"""
import inspect
import itertools
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.resume import Resume
from app.models.resume_analysis import ResumeAnalysis
from app.models.user import User
from app.services import ai_service as ai_service_module
from app.services import gemini_service, ollama_service
from app.services.ai_service import (
    FallbackAIService,
    GeminiAIService,
    NullAIService,
    OllamaAIService,
    build_ai_service,
    get_ai_service,
    set_ai_service,
)
from app.services.interview_engine import InterviewEngine
from app.services.interview_strategies import (
    HR_STRATEGY,
    TECHNICAL_STRATEGY,
    AnswerEvaluationRequest,
    QuestionRequest,
)
from app.services.json_response import parse_json_safely

SERVICES_DIR = Path(ollama_service.__file__).resolve().parent


# =============================================================================
# Mocked Ollama HTTP layer
# =============================================================================

class FakeResponse:
    """Minimal stand-in for `httpx.Response`."""

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ollama.invalid/api/chat")
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )


class FakeClient:
    """Records requests and replays a scripted list of replies/exceptions."""

    def __init__(self, calls: List[Dict[str, Any]], script: List[Any], kwargs: Dict[str, Any]):
        self._calls = calls
        self._script = script
        calls.append({"client_kwargs": kwargs})

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *exc_info: Any) -> bool:
        return False

    def post(self, url: str, json: Any = None, **kwargs: Any) -> Any:
        self._calls.append({"method": "POST", "url": url, "payload": json})
        return self._next()

    def get(self, url: str, **kwargs: Any) -> Any:
        self._calls.append({"method": "GET", "url": url})
        return self._next()

    def _next(self) -> Any:
        if not self._script:
            raise AssertionError("Ollama was called more times than the test scripted.")
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            item = item()
        # A bare dict is shorthand for a 200 response carrying that JSON body.
        if isinstance(item, dict):
            return FakeResponse(item)
        return item


def install_fake_ollama(monkeypatch: pytest.MonkeyPatch, *scripted: Any) -> List[Dict[str, Any]]:
    """
    Replaces the Ollama HTTP boundary with a fake client.

    Each scripted item is a dict payload, a `FakeResponse`, a callable returning
    either, or an exception instance to raise. Returns the call log.
    """
    calls: List[Dict[str, Any]] = []
    script = list(scripted)

    def factory(**kwargs: Any) -> FakeClient:
        return FakeClient(calls, script, kwargs)

    monkeypatch.setattr(ollama_service.httpx, "Client", factory)
    return calls


def ollama_chat_reply(content: str, model: str = "llama3.2:3b") -> Dict[str, Any]:
    """A successful `/api/chat` response body."""
    return {
        "model": model,
        "created_at": "2026-01-01T00:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
    }


# Payloads a real local model would return for the interview schemas.
OLLAMA_TECHNICAL_QUESTION = {
    "question": "How would you structure a FastAPI service so the interview engine stays provider-agnostic?",
    "topic": "architecture",
    "difficulty": "hard",
    "source_context": "Built a layered FastAPI backend with JWT auth.",
}
OLLAMA_TECHNICAL_EVALUATION = {
    "overall_score": 8.4,
    "technical_accuracy": 9.0,
    "relevance": 8.5,
    "depth": 8.0,
    "clarity": 8.0,
    "feedback": "Clear reasoning about layering and dependency injection.",
    "strengths": ["Named the abstraction boundary.", "Mentioned testability."],
    "improvements": ["Discuss failure modes explicitly."],
    "follow_up_needed": False,
}
OLLAMA_HR_QUESTION = {
    "question": "Tell me about a time you owned a project that was at risk of slipping.",
    "category": "project_behavioral",
    "difficulty": "medium",
    "source_context": "Resume lists a FastAPI + Next.js platform shipped under deadline.",
}
OLLAMA_HR_EVALUATION = {
    "relevance_score": 8.5,
    "clarity_score": 8.0,
    "specificity_score": 7.5,
    "communication_score": 8.5,
    "self_awareness_score": 8.0,
    "behavioral_evidence_score": 7.5,
    "overall_score": 8.0,
    "feedback": "Good ownership story with a concrete recovery action.",
    "strengths": ["Described a specific recovery plan."],
    "improvement_points": ["Quantify the schedule impact."],
    "star_feedback": {
        "situation": "Present",
        "task": "Present",
        "action": "Present",
        "result": "Partially Present",
        "guidance": "Add the measurable outcome.",
    },
    "follow_up_needed": False,
}


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ollama_env(monkeypatch: pytest.MonkeyPatch):
    """Ollama configured, no cloud credentials, no overrides."""
    gemini_service.set_gemini_override(None)
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setattr(settings, "OLLAMA_TIMEOUT_SECONDS", 120)
    monkeypatch.setattr(settings, "OLLAMA_TEMPERATURE", 0.7)
    monkeypatch.setattr(settings, "OLLAMA_MAX_TOKENS", 2048)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    yield
    gemini_service.set_gemini_override(None)
    set_ai_service(None)


@pytest.fixture
def user_factory(db_session):
    counter = itertools.count(1)

    def _make() -> User:
        user = User(
            name="Ollama Tester",
            email=f"ollama_user_{next(counter)}@test.com",
            hashed_password="not-used",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture
def seeded_resume(db_session, user_factory):
    """A parsed + analyzed active resume, as the engine requires."""
    user = user_factory()
    resume = Resume(
        user_id=user.id,
        original_filename="ollama_resume.pdf",
        file_path="uploads/resumes/ollama_resume.pdf",
        version_number=1,
        is_active=True,
        extracted_text="Python FastAPI developer with PostgreSQL and Next.js experience.",
    )
    db_session.add(resume)
    db_session.flush()
    db_session.add(
        ResumeAnalysis(
            resume_id=resume.id,
            extracted_skills=[{"skill": "Python"}, {"skill": "FastAPI"}],
            experience=[
                {"title": "Software Engineer Intern", "company": "TechCorp", "duration": "2024"}
            ],
            projects=[
                {
                    "name": "CareerPilot AI",
                    "technologies": ["FastAPI", "Next.js"],
                    "description": "Interview platform with AI scoring.",
                }
            ],
        )
    )
    db_session.commit()
    db_session.refresh(resume)
    return user, resume


# =============================================================================
# 1. Provider selection via AI_PROVIDER
# =============================================================================

def test_ai_provider_ollama_selects_ollama_service(ollama_env):
    service = get_ai_service()
    assert isinstance(service, OllamaAIService)
    assert service.is_available() is True


def test_ai_provider_gemini_selects_gemini_service(monkeypatch: pytest.MonkeyPatch):
    gemini_service.set_gemini_override(None)
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    assert isinstance(get_ai_service(), GeminiAIService)
    gemini_service.set_gemini_override(None)


@pytest.mark.parametrize("value", ["none", "disabled", "off", "NULL", ""])
def test_ai_provider_disabled_returns_null_service(monkeypatch: pytest.MonkeyPatch, value: str):
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", value)
    service = get_ai_service()
    assert isinstance(service, NullAIService)
    assert service.is_available() is False
    assert service.generate_json("prompt") is None


def test_ai_provider_is_case_insensitive(monkeypatch: pytest.MonkeyPatch):
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "  Ollama  ")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    assert isinstance(get_ai_service(), OllamaAIService)


def test_unknown_provider_warns_and_uses_gemini(monkeypatch: pytest.MonkeyPatch, caplog):
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "definitely-not-a-provider")
    with caplog.at_level("WARNING"):
        service = build_ai_service()
    assert isinstance(service, GeminiAIService)
    assert "AI_PROVIDER" in caplog.text


def test_ollama_is_primary_with_gemini_as_optional_fallback(monkeypatch: pytest.MonkeyPatch):
    gemini_service.set_gemini_override(None)
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")

    service = get_ai_service()
    assert isinstance(service, FallbackAIService)
    assert len(service) == 2
    assert isinstance(service.services[0], OllamaAIService)  # local first
    assert isinstance(service.services[1], GeminiAIService)  # cloud backup
    gemini_service.set_gemini_override(None)


def test_ollama_alone_when_no_gemini_credentials(ollama_env):
    service = get_ai_service()
    assert isinstance(service, OllamaAIService)
    assert not isinstance(service, FallbackAIService)


def test_ollama_without_model_prefers_gemini_then_null(monkeypatch: pytest.MonkeyPatch):
    gemini_service.set_gemini_override(None)
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")  # nothing pulled

    # No cloud credential either -> deterministic fallbacks only.
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    assert isinstance(build_ai_service(), NullAIService)

    # With a credential, Gemini carries the load instead of losing all AI.
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")
    assert isinstance(build_ai_service(), GeminiAIService)
    gemini_service.set_gemini_override(None)


def test_injected_service_overrides_environment(ollama_env):
    class Stub(OllamaAIService):
        pass

    stub = NullAIService()
    set_ai_service(stub)
    assert get_ai_service() is stub
    set_ai_service(None)
    assert isinstance(get_ai_service(), OllamaAIService)


# =============================================================================
# 2. Ollama transport: success, parsing, failures
# =============================================================================

def test_successful_generation_returns_parsed_json(ollama_env, monkeypatch):
    calls = install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps(OLLAMA_HR_QUESTION)))

    result = OllamaAIService().generate_json("prompt text", "system rules")

    assert result == OLLAMA_HR_QUESTION
    post = next(c for c in calls if c.get("method") == "POST")
    assert post["url"] == "http://ollama.test:11434/api/chat"
    payload = post["payload"]
    assert payload["model"] == "llama3.2:3b"
    assert payload["stream"] is False
    assert payload["format"] == "json"
    assert payload["messages"][0] == {"role": "system", "content": "system rules"}
    assert payload["messages"][-1] == {"role": "user", "content": "prompt text"}
    assert payload["options"]["temperature"] == 0.7
    assert payload["options"]["num_predict"] == 2048
    # Timeout comes from configuration, not a hardcoded constant.
    assert any(c.get("client_kwargs", {}).get("timeout") == 120 for c in calls)


def test_model_and_url_come_from_environment(ollama_env, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://gpu-box.lan:9999/")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen2.5:14b")
    calls = install_fake_ollama(monkeypatch, ollama_chat_reply('{"question": "Why?"}'))

    OllamaAIService().generate_json("p")

    post = next(c for c in calls if c.get("method") == "POST")
    assert post["url"] == "http://gpu-box.lan:9999/api/chat"  # trailing slash normalized
    assert post["payload"]["model"] == "qwen2.5:14b"


def test_markdown_fenced_json_is_parsed(ollama_env, monkeypatch):
    fenced = "```json\n" + json.dumps(OLLAMA_TECHNICAL_QUESTION) + "\n```"
    install_fake_ollama(monkeypatch, ollama_chat_reply(fenced))
    assert OllamaAIService().generate_json("p") == OLLAMA_TECHNICAL_QUESTION


def test_json_embedded_in_prose_is_parsed(ollama_env, monkeypatch):
    noisy = (
        "Sure! Here is the JSON you asked for:\n"
        + json.dumps(OLLAMA_TECHNICAL_QUESTION)
        + "\nLet me know if you need changes."
    )
    install_fake_ollama(monkeypatch, ollama_chat_reply(noisy))
    assert OllamaAIService().generate_json("p") == OLLAMA_TECHNICAL_QUESTION


def test_generate_style_response_is_supported(ollama_env, monkeypatch):
    """A `/api/generate`-shaped body still parses."""
    install_fake_ollama(monkeypatch, {"response": json.dumps(OLLAMA_HR_QUESTION), "done": True})
    assert OllamaAIService().generate_json("p") == OLLAMA_HR_QUESTION


@pytest.mark.parametrize(
    "content",
    [
        "{not valid json at all",
        "[1, 2, 3]",  # valid JSON, but not an object
        "",
        "   ",
        "I refuse to answer in JSON.",
    ],
)
def test_malformed_or_unusable_responses_return_none(ollama_env, monkeypatch, content: str):
    install_fake_ollama(monkeypatch, ollama_chat_reply(content))
    assert OllamaAIService().generate_json("p") is None


def test_missing_message_content_returns_none(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, {"model": "llama3.2:3b", "message": {}, "done": True})
    assert OllamaAIService().generate_json("p") is None


def test_http_error_status_returns_none(ollama_env, monkeypatch):
    install_fake_ollama(
        monkeypatch,
        FakeResponse({"error": 'model "llama3.2:3b" not found, try pulling it first'}, 404),
    )
    assert OllamaAIService().generate_json("p") is None


def test_timeout_returns_none(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, httpx.TimeoutException("timed out"))
    assert OllamaAIService().generate_json("p") is None


def test_connection_refused_returns_none(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, httpx.ConnectError("connection refused"))
    assert OllamaAIService().generate_json("p") is None


def test_undecodable_body_returns_none(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, FakeResponse(ValueError("not json")))
    assert OllamaAIService().generate_json("p") is None


def test_unexpected_exception_is_swallowed(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, RuntimeError("boom"))
    assert OllamaAIService().generate_json("p") is None


def test_not_configured_makes_no_http_call(monkeypatch: pytest.MonkeyPatch):
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    calls = install_fake_ollama(monkeypatch)  # any HTTP call fails the test
    service = OllamaAIService()
    assert service.is_available() is False
    assert service.generate_json("p") is None
    assert calls == []


def test_reachability_and_model_listing(ollama_env, monkeypatch):
    install_fake_ollama(
        monkeypatch,
        FakeResponse({"models": [{"name": "llama3.2:3b"}, {"name": "qwen2.5:14b"}]}),
        FakeResponse({"models": [{"name": "llama3.2:3b"}, {"name": "qwen2.5:14b"}]}),
    )
    assert ollama_service.is_ollama_reachable() is True
    assert ollama_service.list_local_models() == ["llama3.2:3b", "qwen2.5:14b"]


def test_reachability_false_when_offline(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, httpx.ConnectError("offline"))
    assert ollama_service.is_ollama_reachable() is False
    assert ollama_service.list_local_models() == []


# =============================================================================
# 3. Shared structured-response contract
# =============================================================================

def test_parse_json_safely_contract():
    assert parse_json_safely('{"a": 1}') == {"a": 1}
    assert parse_json_safely('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_safely('```\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_safely('prefix {"a": 1} suffix') == {"a": 1}
    assert parse_json_safely('{"a": 1}') == {"a": 1}
    assert parse_json_safely("no json here") is None
    assert parse_json_safely("") is None
    assert parse_json_safely(None) is None
    assert parse_json_safely("[1,2]") is None  # not an object


def test_gemini_parser_is_the_shared_parser():
    assert gemini_service._parse_json_safely('{"a": 1}') == {"a": 1}
    assert gemini_service._parse_json_safely("nope") is None


# =============================================================================
# 4. Fallback chain behaviour
# =============================================================================

def test_fallback_prefers_the_first_working_provider(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps({"question": "from ollama"})))

    class Boom(GeminiAIService):
        def generate_json(self, prompt, system_instruction=None):
            raise AssertionError("Gemini must not be called when Ollama succeeds")

    service = FallbackAIService([OllamaAIService(), Boom()])
    assert service.generate_json("p") == {"question": "from ollama"}


def test_fallback_moves_to_gemini_when_ollama_returns_none(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, httpx.TimeoutException("timed out"))
    gemini = GeminiAIService()
    gemini.generate_json = lambda prompt, system_instruction=None: {"question": "from gemini"}  # type: ignore[assignment]
    assert FallbackAIService([OllamaAIService(), gemini]).generate_json("p") == {
        "question": "from gemini"
    }


def test_fallback_skips_provider_that_raises(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps({"question": "recovered"})))

    class Exploding(OllamaAIService):
        def generate_json(self, prompt, system_instruction=None):
            raise RuntimeError("provider exploded")

    service = FallbackAIService([Exploding(), OllamaAIService()])
    assert service.generate_json("p") == {"question": "recovered"}


def test_fallback_returns_none_when_every_provider_fails(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, httpx.ConnectError("offline"))
    dead = NullAIService()
    assert FallbackAIService([OllamaAIService(), dead]).generate_json("p") is None
    assert FallbackAIService([]).generate_json("p") is None


def test_fallback_is_available_when_any_provider_is(ollama_env):
    assert FallbackAIService([NullAIService(), OllamaAIService()]).is_available() is True
    assert FallbackAIService([NullAIService()]).is_available() is False


def test_gemini_answers_when_ollama_is_down(ollama_env, monkeypatch):
    """End-to-end: AI_PROVIDER=ollama + Gemini override still produces content."""
    install_fake_ollama(monkeypatch, httpx.ConnectError("offline"))

    class StubGemini:
        def call_ai_api(self, prompt, system_instruction=None):
            return dict(OLLAMA_TECHNICAL_QUESTION)

    monkeypatch.setattr(gemini_service, "call_ai_api", StubGemini().call_ai_api)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key")

    payload = TECHNICAL_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Skills: Python, FastAPI",
            question_number=1,
            total_questions=3,
            target_difficulty="medium",
        ),
        get_ai_service(),
    )
    assert payload["question"] == OLLAMA_TECHNICAL_QUESTION["question"]


# =============================================================================
# 5. Strategies driven by Ollama (through AIService only)
# =============================================================================

def test_technical_question_uses_ollama(ollama_env, monkeypatch):
    calls = install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps(OLLAMA_TECHNICAL_QUESTION)))

    payload = TECHNICAL_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Skills: Python, FastAPI\nProject: CareerPilot AI",
            job_context="Target Position: Backend Engineer",
            question_number=1,
            total_questions=5,
            target_difficulty="medium",
        ),
        OllamaAIService(),
    )

    assert payload["question"] == OLLAMA_TECHNICAL_QUESTION["question"]
    assert payload["topic"] == "architecture"
    assert payload["difficulty"] == "hard"
    assert payload["source_context"] == OLLAMA_TECHNICAL_QUESTION["source_context"]
    # The prompt still carries the Phase A context markers.
    sent = next(c for c in calls if c.get("method") == "POST")["payload"]
    assert sent["messages"][-1]["content"].count("Candidate") >= 1


def test_technical_evaluation_uses_ollama(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps(OLLAMA_TECHNICAL_EVALUATION)))

    evaluation = TECHNICAL_STRATEGY.evaluate_answer(
        AnswerEvaluationRequest(
            question_text=OLLAMA_TECHNICAL_QUESTION["question"],
            answer_text="I kept the engine provider-agnostic behind an interface.",
            candidate_context="Skills: Python",
        ),
        OllamaAIService(),
    )

    assert evaluation["score"] == 8.4
    assert evaluation["technical_accuracy"] == 9.0
    assert evaluation["relevance"] == 8.5
    assert evaluation["depth"] == 8.0
    assert evaluation["clarity"] == 8.0
    assert evaluation["strengths"] == OLLAMA_TECHNICAL_EVALUATION["strengths"]
    assert evaluation["follow_up_needed"] is False


def test_hr_question_uses_ollama(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps(OLLAMA_HR_QUESTION)))

    payload = HR_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Skills: Python\nProject: CareerPilot AI",
            question_number=2,
            total_questions=5,
            target_category="project_behavioral",
            target_difficulty="medium",
        ),
        OllamaAIService(),
    )

    assert payload["question"] == OLLAMA_HR_QUESTION["question"]
    assert payload["category"] == "project_behavioral"
    assert payload["difficulty"] == "medium"


def test_hr_evaluation_uses_ollama(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, ollama_chat_reply(json.dumps(OLLAMA_HR_EVALUATION)))

    evaluation = HR_STRATEGY.evaluate_answer(
        AnswerEvaluationRequest(
            question_text=OLLAMA_HR_QUESTION["question"],
            answer_text="I owned the timeline, replanned the backlog and shipped on time.",
            candidate_context="Project: CareerPilot AI",
        ),
        OllamaAIService(),
    )

    assert evaluation["relevance_score"] == 8.5
    assert evaluation["communication_score"] == 8.5
    assert evaluation["behavioral_evidence_score"] == 7.5
    assert evaluation["star_feedback"]["result"] == "Partially Present"
    assert evaluation["improvement_points"] == OLLAMA_HR_EVALUATION["improvement_points"]


@pytest.mark.parametrize(
    "strategy,kwargs",
    [
        (TECHNICAL_STRATEGY, {}),
        (HR_STRATEGY, {"target_category": "behavioral"}),
    ],
)
def test_strategies_fall_back_when_ollama_is_unusable(ollama_env, monkeypatch, strategy, kwargs):
    """Malformed provider output must never leak into the interview."""
    install_fake_ollama(monkeypatch, ollama_chat_reply("sorry, no JSON for you"))

    payload = strategy.generate_question(
        QuestionRequest(
            candidate_context="Skills: Python, FastAPI\nProject: CareerPilot AI",
            question_number=1,
            total_questions=3,
            target_difficulty="medium",
            **kwargs,
        ),
        OllamaAIService(),
    )

    assert isinstance(payload["question"], str) and len(payload["question"]) > 10
    assert "sorry, no JSON" not in payload["question"]
    assert payload["difficulty"] == "medium"


def test_strategies_fall_back_when_ollama_times_out(ollama_env, monkeypatch):
    install_fake_ollama(monkeypatch, httpx.TimeoutException("timed out"))
    evaluation = TECHNICAL_STRATEGY.evaluate_answer(
        AnswerEvaluationRequest(
            question_text="Explain dependency injection.",
            answer_text="Inversion of control via constructor arguments keeps services testable.",
            candidate_context="Skills: Python",
        ),
        OllamaAIService(),
    )
    assert 0.0 <= evaluation["score"] <= 10.0
    assert evaluation["feedback"]


# =============================================================================
# 6. Full interviews end to end through Ollama
# =============================================================================

def test_technical_interview_runs_on_ollama(db_session, seeded_resume, ollama_env, monkeypatch):
    user, resume = seeded_resume
    calls = install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(json.dumps(OLLAMA_TECHNICAL_QUESTION)),
        ollama_chat_reply(json.dumps(OLLAMA_TECHNICAL_EVALUATION)),
        ollama_chat_reply(json.dumps({**OLLAMA_TECHNICAL_QUESTION, "difficulty": "hard"})),
    )
    engine = InterviewEngine(db=db_session, strategy=TECHNICAL_STRATEGY, ai_service=get_ai_service())

    interview, _, _ = engine.start_interview(user_id=user.id, resume_id=resume.id, total_questions=2)
    first = engine.get_current_question(interview)

    # Q1 came from Ollama, not from the deterministic templates.
    assert first.question_text == OLLAMA_TECHNICAL_QUESTION["question"]
    assert first.topic == "architecture"
    assert first.difficulty == "hard"

    result = engine.submit_answer(
        interview_id=interview.id,
        user_id=user.id,
        answer_text="I introduced an AIService interface so the engine never imports a vendor.",
    )
    assert result["completed"] is False
    assert result["answer_evaluation"]["score"] == 8.4
    assert result["next_question"]["question_text"] == OLLAMA_TECHNICAL_QUESTION["question"]

    # Two AI calls so far: one question, one evaluation.
    assert len([c for c in calls if c.get("method") == "POST"]) == 3


def test_hr_interview_runs_on_ollama(db_session, seeded_resume, ollama_env, monkeypatch):
    user, resume = seeded_resume
    install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(json.dumps(OLLAMA_HR_QUESTION)),
        ollama_chat_reply(json.dumps(OLLAMA_HR_EVALUATION)),
    )
    engine = InterviewEngine(db=db_session, strategy=HR_STRATEGY, ai_service=get_ai_service())

    interview, _, _ = engine.start_interview(user_id=user.id, resume_id=resume.id, total_questions=2)
    # Q1 is always the introduction framing; Ollama supplies the wording.
    assert engine.get_current_question(interview).question_text == OLLAMA_HR_QUESTION["question"]

    result = engine.submit_answer(
        interview_id=interview.id,
        user_id=user.id,
        answer_text="When the deadline slipped I replanned the backlog daily and shipped on time.",
    )
    evaluation = result["answer_evaluation"]
    assert evaluation["overall_score"] == 8.0
    assert evaluation["star_feedback"]["action"] == "Present"
    assert result["completed"] is False

    db_session.refresh(interview)
    assert interview.questions[0].answer is not None


def test_technical_interview_falls_back_when_ollama_is_down(
    db_session, seeded_resume, ollama_env, monkeypatch
):
    user, resume = seeded_resume
    install_fake_ollama(monkeypatch, httpx.ConnectError("offline"))
    engine = InterviewEngine(db=db_session, strategy=TECHNICAL_STRATEGY, ai_service=get_ai_service())

    interview, _, _ = engine.start_interview(user_id=user.id, resume_id=resume.id, total_questions=2)
    first = engine.get_current_question(interview)
    assert first.question_text  # deterministic template still produced a question

    result = engine.submit_answer(
        interview_id=interview.id,
        user_id=user.id,
        answer_text="I structured the code into services, strategies and thin API routes.",
    )
    assert 0.0 <= result["answer_evaluation"]["score"] <= 10.0
    assert result["next_question"]["question_text"]


def test_answer_contract_is_unchanged_with_ollama(
    db_session, seeded_resume, ollama_env, monkeypatch
):
    """audio -> transcript -> normalize_answer_text() -> process_answer()."""
    user, resume = seeded_resume
    install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(json.dumps(OLLAMA_TECHNICAL_QUESTION)),
        ollama_chat_reply(json.dumps(OLLAMA_TECHNICAL_EVALUATION)),
    )
    engine = InterviewEngine(db=db_session, strategy=TECHNICAL_STRATEGY, ai_service=get_ai_service())
    interview, _, _ = engine.start_interview(user_id=user.id, resume_id=resume.id, total_questions=2)

    transcript = "  I introduced an AIService interface so the engine stays vendor-agnostic.  "
    normalized = engine.normalize_answer_text(transcript)
    assert normalized == transcript.strip()

    # The same seam a future transcription step would call.
    result = engine.submit_answer(
        interview_id=interview.id, user_id=user.id, answer_text=normalized
    )
    assert result["answer_evaluation"]["score"] == 8.4

    db_session.refresh(interview)
    persisted = interview.questions[0].answer
    assert persisted.answer_text == normalized
    assert persisted.overall_score == 8.4

    with pytest.raises(HTTPException) as exc:
        engine.submit_answer(interview_id=interview.id, user_id=user.id, answer_text="   ")
    assert exc.value.status_code == 422


def test_empty_ollama_completion_does_not_break_an_interview(
    db_session, seeded_resume, ollama_env, monkeypatch
):
    user, resume = seeded_resume
    install_fake_ollama(monkeypatch, {"message": {"content": ""}, "done": True})
    engine = InterviewEngine(db=db_session, strategy=TECHNICAL_STRATEGY, ai_service=get_ai_service())
    interview, _, _ = engine.start_interview(user_id=user.id, resume_id=resume.id, total_questions=2)
    assert engine.get_current_question(interview).question_text


# =============================================================================
# 7. Local-model output normalization (found by the real Ollama smoke test)
# =============================================================================

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("architecture | problem_solving | resume_project", "architecture"),
        ("behavioral, collaboration", "behavioral"),
        (["problem_solving", "architecture"], "problem_solving"),
        ("  debugging  ", "debugging"),
        ("**security**", "security"),
        ("", "technical_skills"),
        ("   ", "technical_skills"),
        (None, "technical_skills"),
        (["", "  "], "technical_skills"),
    ],
)
def test_topic_is_reduced_to_a_single_label(ollama_env, monkeypatch, raw, expected):
    """A 3B model answers `topic` with a list or a pipe-separated run."""
    install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(
            json.dumps({**OLLAMA_TECHNICAL_QUESTION, "topic": raw})
        ),
    )
    payload = TECHNICAL_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Skills: Python",
            question_number=1,
            total_questions=3,
            target_difficulty="medium",
        ),
        OllamaAIService(),
    )
    assert payload["topic"] == expected
    assert "|" not in payload["topic"]


def test_hr_category_must_be_a_known_category(ollama_env, monkeypatch):
    """An invented category must not be persisted, since it drives progression."""
    install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(
            json.dumps({**OLLAMA_HR_QUESTION, "category": "teamwork | conflict"})
        ),
    )
    payload = HR_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Project: CareerPilot AI",
            question_number=2,
            total_questions=5,
            target_category="project_behavioral",
            target_difficulty="medium",
        ),
        OllamaAIService(),
    )
    assert payload["category"] == "project_behavioral"


def test_hr_accepts_a_known_category_from_the_model(ollama_env, monkeypatch):
    install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(json.dumps({**OLLAMA_HR_QUESTION, "category": "career_goals"})),
    )
    payload = HR_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Project: CareerPilot AI",
            question_number=2,
            total_questions=5,
            target_category="project_behavioral",
            target_difficulty="medium",
        ),
        OllamaAIService(),
    )
    assert payload["category"] == "career_goals"


def test_normalized_topic_reaches_the_database(db_session, seeded_resume, ollama_env, monkeypatch):
    user, resume = seeded_resume
    install_fake_ollama(
        monkeypatch,
        ollama_chat_reply(
            json.dumps(
                {**OLLAMA_TECHNICAL_QUESTION, "topic": "architecture | problem_solving"}
            )
        ),
    )
    engine = InterviewEngine(db=db_session, strategy=TECHNICAL_STRATEGY, ai_service=get_ai_service())
    interview, _, _ = engine.start_interview(user_id=user.id, resume_id=resume.id, total_questions=2)

    db_session.refresh(interview)
    assert interview.questions[0].topic == "architecture"


# =============================================================================
# 7. Gemini remains selectable
# =============================================================================

def test_gemini_service_still_works_through_ai_service(monkeypatch: pytest.MonkeyPatch):
    gemini_service.set_gemini_override(None)
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")

    class MockGemini:
        def __init__(self):
            self.call_count = 0

        def call_ai_api(self, prompt, system_instruction=None):
            self.call_count += 1
            return dict(OLLAMA_TECHNICAL_QUESTION)

    mock = MockGemini()
    monkeypatch.setattr(gemini_service, "call_ai_api", mock.call_ai_api)

    service = get_ai_service()
    assert isinstance(service, GeminiAIService)
    assert service.generate_json("p") == OLLAMA_TECHNICAL_QUESTION
    assert mock.call_count == 1


def test_gemini_override_hook_is_honoured_by_the_adapter(monkeypatch: pytest.MonkeyPatch):
    gemini_service.set_gemini_override(None)
    set_ai_service(None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")

    class MockGemini:
        """Mirrors the legacy override contract (generate_json / callable)."""

        def generate_json(self, prompt, system_instruction=None):
            return {"question": "legacy mock question that is long enough"}

    gemini_service.set_gemini_override(MockGemini())
    payload = TECHNICAL_STRATEGY.generate_question(
        QuestionRequest(
            candidate_context="Skills: Python",
            question_number=1,
            total_questions=3,
            target_difficulty="medium",
        ),
        get_ai_service(),
    )
    assert payload["question"] == "legacy mock question that is long enough"
    gemini_service.set_gemini_override(None)


def test_gemini_transport_imports_are_intact():
    assert hasattr(gemini_service, "call_ai_api")
    assert hasattr(gemini_service, "set_gemini_override")
    assert hasattr(gemini_service, "has_ai_backend")
    # The interview wrappers still delegate to the strategies.
    assert hasattr(gemini_service, "generate_technical_question")
    assert hasattr(gemini_service, "generate_hr_question")
    assert gemini_service.HR_QUESTION_CATEGORIES


# =============================================================================
# 8. Architecture boundaries
# =============================================================================

def test_ollama_module_has_no_interview_logic():
    source = inspect.getsource(ollama_service)
    for forbidden in ("interview_engine", "interview_strategies", "TECHNICAL_STRATEGY", "HR_STRATEGY"):
        assert forbidden not in source


def test_ollama_module_does_not_hardcode_model_or_url():
    source = inspect.getsource(ollama_service).lower()
    assert "llama3.2" not in source
    assert "11434" not in source


def test_ollama_module_reads_configuration_from_settings():
    source = inspect.getsource(ollama_service)
    assert "settings.OLLAMA_BASE_URL" in source
    assert "settings.OLLAMA_MODEL" in source
    assert "settings.OLLAMA_TIMEOUT_SECONDS" in source


def test_engine_knows_nothing_about_ollama():
    from app.services import interview_engine

    source = inspect.getsource(interview_engine).lower()
    for forbidden in ("ollama", "gemini", "openrouter", "httpx"):
        assert forbidden not in source


def test_strategies_know_nothing_about_ollama():
    from app.services import interview_strategies

    source = inspect.getsource(interview_strategies).lower()
    for forbidden in ("ollama", "gemini", "openrouter", "httpx", "11434"):
        assert forbidden not in source


def test_ollama_is_reached_only_through_ai_service():
    source = inspect.getsource(ai_service_module)
    assert "OllamaAIService" in source
    assert "ollama_service" in source  # the only place that imports the transport
    # No other interview module imports or calls the Ollama transport.
    for module_name in ("interview_engine", "interview_strategies", "gemini_service"):
        module_source = inspect.getsource(
            __import__(f"app.services.{module_name}", fromlist=["x"])
        )
        for forbidden in ("import ollama_service", "from app.services import ollama", "ollama_service."):
            assert forbidden not in module_source, f"{module_name} must not use {forbidden}"


def test_ollama_provider_is_reusable_by_any_strategy():
    """Any AIService implementation is interchangeable - strategies are generic."""
    service = OllamaAIService()
    assert hasattr(service, "generate_json") and hasattr(service, "is_available")
    assert isinstance(service, ai_service_module.AIService)


# =============================================================================
# 9. Opt-in real smoke test (requires a running Ollama)
# =============================================================================

@pytest.mark.skipif(
    os.getenv("RUN_OLLAMA_SMOKE") != "1",
    reason="Set RUN_OLLAMA_SMOKE=1 to test against a real local Ollama server.",
)
def test_real_ollama_generates_technical_and_hr_question():
    gemini_service.set_gemini_override(None)
    set_ai_service(None)

    # Force the real Ollama provider, whatever the local .env says.
    settings.AI_PROVIDER = "ollama"
    model = os.getenv("OLLAMA_MODEL") or settings.OLLAMA_MODEL
    settings.OLLAMA_MODEL = model
    base = os.getenv("OLLAMA_BASE_URL") or settings.OLLAMA_BASE_URL
    settings.OLLAMA_BASE_URL = base
    # Local generation on CPU can be slow.
    settings.OLLAMA_TIMEOUT_SECONDS = 300

    assert ollama_service.is_ollama_reachable(), f"Ollama is not reachable at {base}"
    assert model in ollama_service.list_local_models(), (
        f"Model '{model}' is not pulled. Available: {ollama_service.list_local_models()}"
    )

    service = get_ai_service()
    assert isinstance(service, (OllamaAIService, FallbackAIService))

    # 0. Prove the local model really answers with parseable JSON, otherwise a
    #    deterministic fallback could make this test pass for the wrong reason.
    probe = ollama_service.call_ollama_api(
        'Return JSON only: {"ready": true, "provider": "ollama"}'
    )
    assert probe is not None, "Local Ollama did not return parseable JSON"
    assert probe.get("ready") is True
    print(f"\n[smoke] raw probe -> {probe}")

    technical_request = QuestionRequest(
        candidate_context="Skills: Python, FastAPI, PostgreSQL\nProject: CareerPilot AI",
        job_context="Target Position: Backend Engineer",
        question_number=1,
        total_questions=5,
        target_difficulty="medium",
    )
    technical = TECHNICAL_STRATEGY.generate_question(technical_request, service)
    technical_fallback = TECHNICAL_STRATEGY.deterministic_question_fallback(
        candidate_context=technical_request.candidate_context,
        job_context=technical_request.job_context,
        question_number=1,
        total_questions=5,
        target_difficulty="medium",
    )
    assert isinstance(technical["question"], str) and len(technical["question"]) > 10
    assert technical["topic"]
    assert technical["question"] != technical_fallback["question"], (
        "Technical question came from the deterministic fallback, not from Ollama"
    )

    hr_request = QuestionRequest(
        candidate_context="Skills: Python, FastAPI\nProject: CareerPilot AI",
        question_number=1,
        total_questions=5,
        target_category="introduction",
        target_difficulty="medium",
    )
    hr = HR_STRATEGY.generate_question(hr_request, service)
    hr_fallback = HR_STRATEGY.deterministic_question_fallback(
        candidate_context=hr_request.candidate_context,
        job_context=None,
        question_number=1,
        total_questions=5,
        target_category="introduction",
        target_difficulty="medium",
    )
    assert isinstance(hr["question"], str) and len(hr["question"]) > 10
    assert hr["category"]
    assert hr["question"] != hr_fallback["question"], (
        "HR question came from the deterministic fallback, not from Ollama"
    )

    print(f"\n[smoke] ollama technical -> {technical['question']}")
    print(f"[smoke]   (topic={technical['topic']}, difficulty={technical['difficulty']})")
    print(f"[smoke] ollama hr         -> {hr['question']}")
    print(f"[smoke]   (category={hr['category']}, difficulty={hr['difficulty']})")
