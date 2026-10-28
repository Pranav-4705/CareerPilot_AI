"""
Local Ollama provider (HTTP transport only).

Like `app.services.gemini_service`, this module is transport only: it knows how
to talk to a local Ollama server and how to turn the reply into the shared
structured-response contract, but it contains no interview logic. Interview code
reaches it exclusively through `app.services.ai_service.OllamaAIService`.

Configuration comes from the environment (see `app.core.config.settings`):
    AI_PROVIDER=ollama
    OLLAMA_BASE_URL=<your local Ollama server>
    OLLAMA_MODEL=<a model you pulled>

Nothing about the URL or model is hardcoded here.

Failure policy: any problem - Ollama not installed, model missing, connection
refused, timeout, non-2xx status, empty completion, malformed JSON - returns
None. The caller (an interview strategy) then falls back to its deterministic
content, so an interview is never blocked by a local provider outage.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.json_response import parse_json_safely

logger = logging.getLogger(__name__)

# Ollama has no "system" role parameter, so the system instruction is sent as a
# leading system message and the prompt as the user message.
_CHAT_PATH = "/api/chat"
_TAGS_PATH = "/api/tags"


def _base_url() -> str:
    """Ollama base URL from the environment, without a trailing slash."""
    return (settings.OLLAMA_BASE_URL or "").strip().rstrip("/")


def _model() -> str:
    """Ollama model name from the environment."""
    return (settings.OLLAMA_MODEL or "").strip()


def has_ollama_backend() -> bool:
    """True when Ollama is configured (base URL and model both present)."""
    return bool(_base_url() and _model())


def is_ollama_reachable(timeout: float = 3.0) -> bool:
    """
    Cheap liveness probe against `/api/tags`.

    Used for logging/diagnostics (never inside the interview hot path).
    """
    base = _base_url()
    if not base:
        return False
    try:
        response = httpx.Client(timeout=timeout).get(f"{base}{_TAGS_PATH}")
        return response.status_code == 200
    except Exception as exc:  # pragma: no cover - depends on local environment
        logger.info("Ollama is not reachable at %s (%s).", base, exc)
        return False


def list_local_models() -> List[str]:
    """Model names available on the local Ollama server (empty when offline)."""
    base = _base_url()
    if not base:
        return []
    try:
        response = httpx.Client(timeout=3.0).get(f"{base}{_TAGS_PATH}")
        response.raise_for_status()
        data = response.json()
        return [
            str(entry.get("name"))
            for entry in (data.get("models") or [])
            if isinstance(entry, dict) and entry.get("name")
        ]
    except Exception as exc:  # pragma: no cover - depends on local environment
        logger.info("Could not list Ollama models at %s (%s).", base, exc)
        return []


def _build_messages(prompt: str, system_instruction: Optional[str]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_content(data: Any) -> Optional[str]:
    """
    Pulls the assistant text out of an Ollama reply.

    `/api/chat` -> {"message": {"content": "..."}}
    `/api/generate` -> {"response": "..."}
    Anything else (including a list of chat messages) is tolerated so a server
    with slightly different output still parses.
    """
    if not isinstance(data, dict):
        return None

    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

    for key in ("response", "content"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def call_ollama_api(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Calls a local Ollama model and returns a parsed JSON object, or None.

    None is returned for every failure mode (not configured, offline, timeout,
    HTTP error, empty or malformed response) so the caller's deterministic
    fallback kicks in.
    """
    if not has_ollama_backend():
        logger.warning(
            "Ollama is not configured (OLLAMA_BASE_URL/OLLAMA_MODEL); "
            "using deterministic fallback content."
        )
        return None

    base = _base_url()
    model = _model()
    payload = {
        "model": model,
        "messages": _build_messages(prompt, system_instruction),
        "stream": False,
        # Ask Ollama for a JSON object instead of free-form prose.
        "format": "json",
        "options": {
            "temperature": settings.OLLAMA_TEMPERATURE,
            "num_predict": settings.OLLAMA_MAX_TOKENS,
        },
    }

    try:
        with httpx.Client(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            response = client.post(f"{base}{_CHAT_PATH}", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        logger.warning("Ollama timed out after %ss; using fallback.", settings.OLLAMA_TIMEOUT_SECONDS)
        return None
    except httpx.HTTPError as exc:
        logger.warning("Ollama request failed (%s); using fallback.", exc)
        return None
    except Exception as exc:  # malformed body, decode error, ...
        logger.warning("Unexpected Ollama failure (%s); using fallback.", exc)
        return None

    content = _extract_content(data)
    if not content:
        error = data.get("error") if isinstance(data, dict) else None
        logger.warning("Ollama returned an empty completion%s.", f": {error}" if error else "")
        return None

    parsed = parse_json_safely(content)
    if parsed is None:
        logger.warning("Ollama response was not valid JSON; using fallback.")
    return parsed


# Backwards-compatible aliases matching the Gemini client naming.
_call_ollama_api = call_ollama_api
_parse_json_safely = parse_json_safely
