"""
AI provider abstraction (Phase 10 architecture refactor, extended in Phase B).

The shared interview engine and the interview strategies only ever talk to the
`AIService` interface. Concrete providers (local Ollama, Gemini/OpenRouter) are
adapted behind this interface, so interview logic never imports a vendor client
directly and never mentions a provider by name.

Provider wiring:
    * `OllamaAIService` adapts the local Ollama HTTP client that lives in
      `app.services.ollama_service` (primary local provider, env-configured).
    * `GeminiAIService` adapts the existing Gemini/OpenRouter HTTP client in
      `app.services.gemini_service` (keeps provider priority, the test override
      hook and JSON parsing). Used as an optional fallback.
    * `FallbackAIService` tries providers in order and returns the first usable
      JSON object, so one provider being down is not fatal.
    * `NullAIService` represents "no provider configured" and always defers to
      the deterministic fallbacks owned by each strategy.
    * `set_ai_service()` allows tests - or a future provider - to inject a
      replacement without touching the engine or the strategies.

Which provider is used is decided by the `AI_PROVIDER` environment variable
(`ollama`, `gemini` or `none`); see `app.core.config.settings`.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Supported values of settings.AI_PROVIDER.
PROVIDER_OLLAMA = "ollama"
PROVIDER_GEMINI = "gemini"
PROVIDER_NONE = "none"
SUPPORTED_PROVIDERS = (PROVIDER_OLLAMA, PROVIDER_GEMINI, PROVIDER_NONE)
_DISABLED_PROVIDERS = {"none", "disabled", "off", "null", ""}


class AIService(ABC):
    """Provider-agnostic "text in, JSON out" interface used by the engine."""

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Returns a parsed JSON object for the given prompt, or None when the
        provider is unavailable or returned an unusable response.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """True when the provider is configured and can be called."""


class NullAIService(AIService):
    """Explicitly disabled provider: never calls out, always triggers fallback."""

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return None

    def is_available(self) -> bool:
        return False


class GeminiAIService(AIService):
    """
    Adapter for the existing Gemini/OpenRouter client.

    `gemini_service.call_ai_api()` keeps the existing provider priority
    (OpenRouter -> Gemini), the unit-test override hook and defensive JSON
    parsing, so behaviour is unchanged for current deployments.
    """

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        from app.services import gemini_service

        return gemini_service.call_ai_api(prompt, system_instruction)

    def is_available(self) -> bool:
        from app.services import gemini_service

        return gemini_service.has_ai_backend()


class OllamaAIService(AIService):
    """
    Adapter for the local Ollama HTTP client.

    `ollama_service.call_ollama_api()` reads the base URL, model and timeout from
    the environment, asks Ollama for JSON output, and reuses the shared
    structured-response parser. Every failure mode (not installed, model
    missing, offline, timeout, HTTP error, empty or malformed reply) returns
    None, which lets the calling strategy fall back to deterministic content.
    """

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        from app.services import ollama_service

        return ollama_service.call_ollama_api(prompt, system_instruction)

    def is_available(self) -> bool:
        from app.services import ollama_service

        return ollama_service.has_ollama_backend()


class FallbackAIService(AIService):
    """
    Tries each provider in order until one returns a usable JSON object.

    Used when a primary provider has an optional secondary: Ollama first with
    Gemini/OpenRouter as backup. An exception or an empty/None result from one
    provider never prevents the next one from being tried, and only when every
    provider fails does the caller receive None and fall back deterministically.
    """

    def __init__(self, services: Iterable[Optional[AIService]], name: str = "fallback"):
        self.services: List[AIService] = [s for s in services if s is not None]
        self.name = name

    def __len__(self) -> int:
        return len(self.services)

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        for service in self.services:
            try:
                result = service.generate_json(prompt, system_instruction)
            except Exception as exc:  # a broken provider must not break the interview
                logger.warning(
                    "AI provider %s raised %s; trying the next provider.",
                    type(service).__name__,
                    exc,
                )
                continue
            if isinstance(result, dict) and result:
                return result
        return None

    def is_available(self) -> bool:
        return any(service.is_available() for service in self.services)


_ai_service_override: Optional[AIService] = None


def set_ai_service(service: Optional[AIService]) -> None:
    """
    Injects an AIService used by the engine and strategies.
    Passing None restores environment-based provider selection.
    """
    global _ai_service_override
    _ai_service_override = service


def _gemini_configured() -> bool:
    """True when Gemini/OpenRouter has a usable credential (or test override)."""
    from app.services import gemini_service

    return gemini_service.has_ai_backend()


def build_ai_service(provider: Optional[str] = None) -> AIService:
    """
    Builds the AIService described by `provider` (default: settings.AI_PROVIDER).

    * `ollama` -> OllamaAIService, plus Gemini/OpenRouter as an optional
      fallback when a credential is configured. When Ollama itself is not
      configured, Gemini becomes the primary so deployments are not silently
      left without AI.
    * `gemini` -> GeminiAIService.
    * `none` (or `disabled`/`off`) -> NullAIService: deterministic fallbacks only.
    * unknown value -> warning, then the `gemini` behaviour.
    """
    from app.core.config import settings

    raw = settings.AI_PROVIDER if provider is None else provider
    name = (raw or "").strip().lower()

    if name in _DISABLED_PROVIDERS:
        return NullAIService()

    if name == PROVIDER_OLLAMA:
        ollama = OllamaAIService()
        if not ollama.is_available():
            logger.warning(
                "AI_PROVIDER=ollama but OLLAMA_BASE_URL/OLLAMA_MODEL are not set. "
                "Pull a model first: `ollama pull llama3.2:3b`."
            )
            if _gemini_configured():
                return GeminiAIService()
            return NullAIService()

        if _gemini_configured():
            # Local first, cloud as a safety net for when Ollama is down.
            return FallbackAIService(
                [ollama, GeminiAIService()], name="ollama+gemini"
            )
        return ollama

    if name != PROVIDER_GEMINI:
        logger.warning(
            "Unknown AI_PROVIDER '%s'. Supported: %s. Falling back to '%s'.",
            raw,
            ", ".join(SUPPORTED_PROVIDERS),
            PROVIDER_GEMINI,
        )

    return GeminiAIService()


def get_ai_service() -> AIService:
    """
    Returns the injected AIService, or builds one from settings.AI_PROVIDER.

    Resolved lazily (never cached) so provider switches and test overrides take
    effect without re-creating the engine or strategies.
    """
    if _ai_service_override is not None:
        return _ai_service_override
    return build_ai_service()
