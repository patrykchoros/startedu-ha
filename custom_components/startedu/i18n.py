from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "en"
DEFAULT_CANCELLED_MEAL_PREFIX = "CANCELLED"
EVENT_TRANSLATION_SECTION = "event"
CANCELLED_MEAL_PREFIX_KEY = "cancelled_meal_prefix"
STATUS_TRANSLATION_SECTION = "status"
TRANSLATIONS: dict[str, dict[str, Any]] = {
    "en": {
        EVENT_TRANSLATION_SECTION: {
            CANCELLED_MEAL_PREFIX_KEY: DEFAULT_CANCELLED_MEAL_PREFIX,
        },
        STATUS_TRANSLATION_SECTION: {
            "available": "available",
            "blocked": "blocked",
            "cancelled": "cancelled",
            "failed": "failed",
            "no_school": "no school",
            "not_ordered": "not ordered",
            "paid": "paid",
            "running": "running",
            "successful": "successful",
            "unpaid": "unpaid",
            "waiting": "waiting",
        },
    },
    "pl": {
        EVENT_TRANSLATION_SECTION: {
            CANCELLED_MEAL_PREFIX_KEY: "ODWO\u0141ANE",
        },
        STATUS_TRANSLATION_SECTION: {
            "available": "dost\u0119pne",
            "blocked": "zablokowane",
            "cancelled": "odwo\u0142ane",
            "failed": "nieudane",
            "no_school": "brak zaj\u0119\u0107",
            "not_ordered": "niezam\u00f3wione",
            "paid": "op\u0142acone",
            "running": "w toku",
            "successful": "udane",
            "unpaid": "nieop\u0142acone",
            "waiting": "oczekuje",
        },
    },
}


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


def status_label(status: str | None, language: str | None = None) -> str | None:
    """Return a localized entity-facing status label."""
    if status is None or status == "unknown":
        return None
    return _translation(
        language,
        STATUS_TRANSLATION_SECTION,
        status,
        fallback=status,
    )


def _translation(
    language: str | None,
    section: str,
    key: str,
    *,
    fallback: str,
) -> str:
    for language_code in _language_candidates(language):
        value = _nested_get(TRANSLATIONS.get(language_code, {}), section, key)
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


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
