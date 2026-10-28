"""
AI provider client (Gemini / OpenRouter) and JSON parsing.

This module is the *transport layer* only. Interview logic no longer depends on
it directly:

  * `app.services.ai_service` exposes the `AIService` interface and adapts this
    client (`GeminiAIService`), so the shared interview engine never imports a
    provider.
  * `app.services.interview_strategies` owns the interview prompts, evaluation
    shaping and deterministic fallbacks.
  * `app.services.json_response` owns the shared structured-response parsing,
    which the local Ollama provider (`app.services.ollama_service`) reuses too.

The interview helper functions at the bottom are thin, deprecated wrappers kept
for backwards compatibility; they delegate to the strategies.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.services.json_response import parse_json_safely

logger = logging.getLogger(__name__)

# Testing mock override hook
_gemini_override: Optional[Any] = None

# Appended to OpenRouter prompts because that API has no structured-output mode.
JSON_ONLY_INSTRUCTION = (
    "\n\nCRITICAL: Respond ONLY with a valid raw JSON object. "
    "Do not include markdown codeblocks or outside text."
)


def set_gemini_override(override_obj: Optional[Any]) -> None:
    """
    Sets a mock object for AI service calls in unit tests.
    """
    global _gemini_override
    _gemini_override = override_obj


def get_gemini_override() -> Optional[Any]:
    """Returns the currently installed test override, if any."""
    return _gemini_override


def has_ai_backend() -> bool:
    """True when a test override or a real provider credential is configured."""
    if _gemini_override is not None:
        return True
    return bool(
        (settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip())
        or (settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    )


def _call_openrouter_api(prompt: str, system_instruction: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Calls the OpenRouter API (supports openrouter/free and other free models).
    Returns parsed JSON dictionary or None on failure.
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key or not api_key.strip():
        return None

    model = settings.OPENROUTER_MODEL or "openrouter/free"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "CareerPilot AI",
    }

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({
        "role": "user",
        "content": prompt + JSON_ONLY_INSTRUCTION,
    })

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, json=payload, headers=headers)
            if res.status_code != 200:
                logger.warning(f"OpenRouter API returned status {res.status_code}: {res.text[:300]}")
                return None
            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content", "")
            return _parse_json_safely(content)
    except Exception as e:
        logger.warning(f"Error communicating with OpenRouter API: {e}")
        return None


def call_ai_api(prompt: str, system_instruction: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Calls the configured external AI backend (OpenRouter first, then Google
    Gemini). Returns a parsed JSON dictionary, or None on failure so callers can
    fall back to deterministic generation.

    Exposed through `app.services.ai_service.GeminiAIService`; the interview
    engine and strategies only use the `AIService` interface.
    """
    if _gemini_override is not None:
        try:
            if hasattr(_gemini_override, "generate_json"):
                return _gemini_override.generate_json(prompt, system_instruction)
            elif callable(_gemini_override):
                return _gemini_override(prompt, system_instruction)
        except Exception as e:
            logger.warning(f"AI override raised exception: {e}. Using fallback.")
            return None

    # Priority 1: OpenRouter (if OPENROUTER_API_KEY is configured)
    if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip():
        or_res = _call_openrouter_api(prompt, system_instruction)
        if or_res:
            return or_res

    # Priority 2: Google Gemini (if GEMINI_API_KEY is configured)
    api_key = settings.GEMINI_API_KEY
    if not api_key or not api_key.strip():
        logger.info("No AI API key set or active. Using deterministic fallback.")
        return None

    model = settings.GEMINI_MODEL or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        },
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            if res.status_code != 200:
                logger.error(f"Gemini API returned status {res.status_code}: {res.text[:300]}")
                return None

            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.error("No candidates in Gemini API response")
                return None

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                return None

            text_output = parts[0].get("text", "")
            return _parse_json_safely(text_output)
    except Exception as e:
        logger.error(f"Error communicating with Gemini API: {e}")
        return None


# Backwards-compatible alias for the previous private name.
_call_gemini_api = call_ai_api


def _parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """Backwards-compatible alias for the shared provider response parser."""
    return parse_json_safely(text)


# ==============================================================================
