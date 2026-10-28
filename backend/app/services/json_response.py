"""
Shared structured-response parsing for AI providers.

Every provider (Gemini/OpenRouter, Ollama, ...) funnels its raw completion text
through `parse_json_safely()` so the interview strategies always receive the
same contract: a JSON object, or `None`.

Handled shapes:
    * plain JSON
    * markdown-fenced JSON (```json ... ``` or ``` ... ```)
    * JSON embedded in surrounding prose (regex extraction)
    * malformed / empty text -> None

Returning `None` is the signal every strategy already handles by falling back to
its deterministic content, so a bad provider response never breaks an interview.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_json_safely(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Parses JSON from raw text or a markdown code fence.

    Returns the decoded object when it is a dict, otherwise None.
    """
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    if not cleaned:
        return None

    try:
        return _coerce_dict(json.loads(cleaned))
    except Exception:
        # Fall back to extracting the outermost JSON object from prose.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return _coerce_dict(json.loads(match.group(0)))
            except Exception:
                pass

    logger.warning("Could not parse a JSON object out of a provider response.")
    return None


def _coerce_dict(value: Any) -> Optional[Dict[str, Any]]:
    """Only dicts satisfy the structured-response contract."""
    if isinstance(value, dict):
        return value
    return None
