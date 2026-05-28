from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from .const import (
    CONF_AFTERNOON_SNACK_TIME,
    CONF_BREAKFAST_TIME,
    CONF_LUNCH_TIME,
    CONF_OTHER_MEAL_TIME,
    DEFAULT_AFTERNOON_SNACK_DURATION_MINUTES,
    DEFAULT_AFTERNOON_SNACK_TIME,
    DEFAULT_BREAKFAST_DURATION_MINUTES,
    DEFAULT_BREAKFAST_TIME,
    DEFAULT_LUNCH_DURATION_MINUTES,
    DEFAULT_LUNCH_TIME,
    DEFAULT_OTHER_MEAL_DURATION_MINUTES,
    DEFAULT_OTHER_MEAL_TIME,
)
from .i18n import cancelled_meal_summary, status_label
from .models import (
    MEAL_STATUS_CANCELLED,
    MEAL_STATUS_NO_SCHOOL,
    MEAL_STATUS_NOT_ORDERED,
    MEAL_STATUS_PAID,
    MEAL_STATUS_UNKNOWN,
    MEAL_STATUS_UNPAID,
    MEAL_TYPE_AFTERNOON_SNACK,
    MEAL_TYPE_BREAKFAST,
    MEAL_TYPE_LUNCH,
    MEAL_TYPE_OTHER,
    StartEduChild,
    StartEduMeal,
)

MAX_STATE_LENGTH = 255
SAFE_MENU_STATE_LENGTH = 240
PRESERVED_MENU_ACRONYMS = frozenset({"BBQ", "BIO", "FIT", "MSC"})


@dataclass(frozen=True, slots=True)
class MealTimeWindow:
    start: datetime
    end: datetime


MEAL_TIME_OPTIONS = {
    MEAL_TYPE_BREAKFAST: (
        CONF_BREAKFAST_TIME,
        DEFAULT_BREAKFAST_TIME,
        DEFAULT_BREAKFAST_DURATION_MINUTES,
    ),
    MEAL_TYPE_LUNCH: (
        CONF_LUNCH_TIME,
        DEFAULT_LUNCH_TIME,
        DEFAULT_LUNCH_DURATION_MINUTES,
    ),
    MEAL_TYPE_AFTERNOON_SNACK: (
        CONF_AFTERNOON_SNACK_TIME,
        DEFAULT_AFTERNOON_SNACK_TIME,
        DEFAULT_AFTERNOON_SNACK_DURATION_MINUTES,
    ),
    MEAL_TYPE_OTHER: (
        CONF_OTHER_MEAL_TIME,
        DEFAULT_OTHER_MEAL_TIME,
        DEFAULT_OTHER_MEAL_DURATION_MINUTES,
    ),
}


def meal_type_from_label(label: str) -> str:
    normalized = _strip_accents(label).casefold()
    if "sniad" in normalized or "breakfast" in normalized:
        return MEAL_TYPE_BREAKFAST
    if "obiad" in normalized or "lunch" in normalized or "dinner" in normalized:
        return MEAL_TYPE_LUNCH
    if "podwiecz" in normalized or "snack" in normalized:
        return MEAL_TYPE_AFTERNOON_SNACK
    return MEAL_TYPE_OTHER


def normalize_meal_label(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if not compact:
        return compact
    return " ".join(_normalize_label_word(word) for word in compact.split(" "))


def meal_time_window(meal: StartEduMeal, options: dict[str, Any]) -> MealTimeWindow:
    option_key, default_value, duration_minutes = MEAL_TIME_OPTIONS.get(
        meal.meal_type,
        MEAL_TIME_OPTIONS[MEAL_TYPE_OTHER],
    )
    start_time = parse_time(options.get(option_key, default_value), default_value)
    start = datetime.combine(meal.date, start_time)
    return MealTimeWindow(start=start, end=start + timedelta(minutes=duration_minutes))


def parse_time(value: Any, default_value: str) -> time:
    candidate = str(value or default_value)
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", candidate):
        candidate = default_value
    hour, minute = (int(part) for part in candidate.split(":"))
    return time(hour=hour, minute=minute)


def calendar_meals(child: StartEduChild) -> tuple[StartEduMeal, ...]:
    return tuple(meal for meal in child.meals if meal.status != MEAL_STATUS_NO_SCHOOL)


def next_child_meal(child: StartEduChild, today: date) -> StartEduMeal | None:
    upcoming = [
        meal
        for meal in child.meals
        if meal.date >= today and meal.status != MEAL_STATUS_NO_SCHOOL
    ]
    active = [meal for meal in upcoming if not meal.is_cancelled]
    return min(active or upcoming, key=lambda meal: meal.date, default=None)


def meal_event_summary(meal: StartEduMeal, language: str | None = None) -> str:
    meal_name = normalize_meal_label(meal.name)
    if meal.is_cancelled:
        return cancelled_meal_summary(meal_name, language)
    return meal_name


def meal_event_description(meal: StartEduMeal) -> str | None:
    if not meal.menu:
        return None
    return normalize_menu_text(meal.menu)


def day_meals(child: StartEduChild, target_date: date) -> tuple[StartEduMeal, ...]:
    return tuple(meal for meal in child.meals if meal.date == target_date)


def has_food(child: StartEduChild, target_date: date) -> bool:
    return any(meal.has_food for meal in day_meals(child, target_date))


def can_cancel(child: StartEduChild, target_date: date) -> bool:
    return any(
        meal.can_cancel and not meal.is_cancelled
        for meal in day_meals(child, target_date)
    )


def day_status(child: StartEduChild, target_date: date) -> str:
    meals = day_meals(child, target_date)
    if not meals:
        return MEAL_STATUS_UNKNOWN

    food_meals = [meal for meal in meals if meal.status != MEAL_STATUS_NO_SCHOOL]
    if not food_meals and any(meal.status == MEAL_STATUS_NO_SCHOOL for meal in meals):
        return MEAL_STATUS_NO_SCHOOL
    if food_meals and all(meal.is_cancelled for meal in food_meals):
        return MEAL_STATUS_CANCELLED
    if any(meal.status == MEAL_STATUS_PAID for meal in food_meals):
        return MEAL_STATUS_PAID
    if any(meal.status == MEAL_STATUS_UNPAID for meal in food_meals):
        return MEAL_STATUS_UNPAID
    if any(meal.status == MEAL_STATUS_NOT_ORDERED for meal in food_meals):
        return MEAL_STATUS_NOT_ORDERED
    return MEAL_STATUS_UNKNOWN


def day_menu_state(
    child: StartEduChild,
    target_date: date,
    language: str | None = None,
) -> str | None:
    meals = [
        meal
        for meal in day_meals(child, target_date)
        if meal.status != MEAL_STATUS_NO_SCHOOL
    ]
    if not meals:
        return None

    parts = []
    for meal in meals:
        label = meal_event_summary(meal, language)
        if meal.menu:
            parts.append(f"{label}: {normalize_menu_text(meal.menu)}")
        else:
            parts.append(label)
    return _truncate_state("; ".join(parts))


def day_menu_attributes(
    child: StartEduChild,
    target_date: date,
    language: str | None = None,
) -> dict[str, Any]:
    meals = [
        meal
        for meal in day_meals(child, target_date)
        if meal.status != MEAL_STATUS_NO_SCHOOL
    ]
    status = day_status(child, target_date)
    full_menu = "\n\n".join(
        f"{meal_event_summary(meal, language)}\n"
        f"{normalize_menu_text(meal.menu) if meal.menu else ''}".strip()
        for meal in meals
    )
    order_numbers = sorted({meal.order_number for meal in meals if meal.order_number})
    return {
        "date": target_date.isoformat(),
        "status": status_label(status, language),
        "status_code": status,
        "is_cancelled": status == MEAL_STATUS_CANCELLED,
        "order_number": order_numbers[0] if len(order_numbers) == 1 else None,
        "order_numbers": order_numbers,
        "full_menu": full_menu or None,
        "meal_slots": [meal_public_attributes(meal, language) for meal in meals],
    }


def meal_public_attributes(
    meal: StartEduMeal,
    language: str | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "date": meal.date.isoformat(),
        "name": normalize_meal_label(meal.name),
        "meal_type": meal.meal_type,
        "can_cancel": meal.can_cancel,
        "is_cancelled": meal.is_cancelled,
        "status": status_label(meal.status, language),
        "status_code": meal.status,
    }
    if meal.menu:
        attributes["menu"] = normalize_menu_text(meal.menu)
    if meal.child_name:
        attributes["child"] = meal.child_name
    if meal.order_number:
        attributes["order_number"] = meal.order_number
    if meal.price is not None:
        attributes["price"] = str(meal.price)
    return attributes


def _truncate_state(value: str) -> str:
    if len(value) <= SAFE_MENU_STATE_LENGTH:
        return value
    return f"{value[: SAFE_MENU_STATE_LENGTH - 1].rstrip()}…"


def normalize_menu_text(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if not compact:
        return compact

    words = list(re.finditer(r"[^\W\d_]+", compact, flags=re.UNICODE))
    if not words:
        return compact

    cased_words = [
        match.group(0)
        for match in words
        if any(char.islower() or char.isupper() for char in match.group(0))
    ]
    if not cased_words:
        return compact

    normalized_words = 0
    sentence_start = True
    result = []
    last_end = 0
    for index, match in enumerate(words):
        result.append(compact[last_end : match.start()])
        word = match.group(0)
        replacement, changed = _normalize_menu_word(word, sentence_start)
        result.append(replacement)
        normalized_words += int(changed)
        last_end = match.end()
        next_start = words[index + 1].start() if index + 1 < len(words) else last_end
        separator = compact[last_end:next_start]
        if re.search(r"[.!?]\s*$", separator):
            sentence_start = True
        else:
            sentence_start = False
    result.append(compact[last_end:])

    if normalized_words == 0:
        return compact
    return "".join(result)


def _normalize_menu_word(word: str, sentence_start: bool) -> tuple[str, bool]:
    if _is_preserved_menu_acronym(word):
        return word, False

    if not (word.isupper() or word.islower()):
        return word, False

    lowered = word.lower()
    if sentence_start:
        replacement = f"{lowered[0].upper()}{lowered[1:]}"
    else:
        replacement = lowered
    return replacement, replacement != word


def _is_short_acronym(word: str) -> bool:
    return word.isupper() and 1 < len(word) <= 3


def _is_preserved_menu_acronym(word: str) -> bool:
    return word.isupper() and word in PRESERVED_MENU_ACRONYMS


def _normalize_label_word(word: str) -> str:
    if _is_short_acronym(word):
        return word
    return f"{word[:1].upper()}{word[1:].lower()}" if word else word


def _strip_accents(value: str) -> str:
    translation = str.maketrans(
        {
            "ą": "a",
            "ć": "c",
            "ę": "e",
            "ł": "l",
            "ń": "n",
            "ó": "o",
            "ś": "s",
            "ż": "z",
            "ź": "z",
            "Ą": "A",
            "Ć": "C",
            "Ę": "E",
            "Ł": "L",
            "Ń": "N",
            "Ó": "O",
            "Ś": "S",
            "Ż": "Z",
            "Ź": "Z",
        }
    )
    return value.translate(translation)
