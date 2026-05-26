from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

DEFAULT_LANGUAGE = "en"
DEFAULT_CANCELLED_MEAL_PREFIX = "CANCELLED"
EVENT_TRANSLATION_SECTION = "event"
CANCELLED_MEAL_PREFIX_KEY = "cancelled_meal_prefix"


def cancelled_meal_prefix(language: str | None = None) -> str:
    """Return the localized cancelled meal prefix."""
    return _translation(
        language,
        EVENT_TRANSLATION_SECTION,
        CANCELLED_MEAL_PREFIX_KEY,
        fallback=DEFAULT_CANCELLED_MEAL_PREFIX,
    )


def cancelled_meal_summary(meal_name: str, language: str | None = None) -> str:
    """Return the localized summary for a cancelled meal."""
    return f"{cancelled_meal_prefix(language)}: {meal_name}"


def _translation(
    language: str | None,
    section: str,
    key: str,
    *,
    fallback: str,
) -> str:
    for language_code in _language_candidates(language):
        value = _nested_get(_load_translation(language_code), section, key)
        if isinstance(value, str) and value:
            return value
    return fallback


def _language_candidates(language: str | None) -> tuple[str, ...]:
    candidates: list[str] = []
    if language:
        normalized = language.replace("_", "-").casefold()
        candidates.append(normalized)
        base_language = normalized.split("-", 1)[0]
        if base_language != normalized:
            candidates.append(base_language)
    candidates.append(DEFAULT_LANGUAGE)
    return tuple(dict.fromkeys(candidates))


@lru_cache(maxsize=None)
def _load_translation(language: str) -> dict[str, Any]:
    base_path = Path(__file__).parent
    paths = [base_path / "translations" / f"{language}.json"]
    if language == DEFAULT_LANGUAGE:
        paths.append(base_path / "strings.json")

    for path in paths:
        if not path.exists():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(loaded, dict):
            return loaded
    return {}


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
