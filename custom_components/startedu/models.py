from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from .i18n import cancelled_meal_summary

MEAL_STATUS_NOT_ORDERED = "not_ordered"
MEAL_STATUS_UNPAID = "unpaid"
MEAL_STATUS_PAID = "paid"
MEAL_STATUS_CANCELLED = "cancelled"
MEAL_STATUS_NO_SCHOOL = "no_school"
MEAL_STATUS_UNKNOWN = "unknown"
ORDER_STATUS_AVAILABLE = "available"
ORDER_STATUS_BLOCKED = "blocked"

MEAL_TYPE_BREAKFAST = "breakfast"
MEAL_TYPE_LUNCH = "lunch"
MEAL_TYPE_AFTERNOON_SNACK = "afternoon_snack"
MEAL_TYPE_OTHER = "other"


@dataclass(frozen=True, slots=True)
class StartEduMeal:
    """A single meal slot entry exposed by StartEdu."""

    meal_id: str | None
    date: date
    name: str
    menu: str | None = None
    meal_type: str = MEAL_TYPE_OTHER
    child_id: str | None = None
    child_name: str | None = None
    status: str = MEAL_STATUS_UNKNOWN
    order_number: str | None = None
    price: Decimal | None = None
    can_cancel: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_cancelled(self) -> bool:
        status = self.status.casefold()
        return "cancel" in status or "odwol" in status or "odwo" in status

    @property
    def has_food(self) -> bool:
        return self.status in {MEAL_STATUS_PAID} and not self.is_cancelled

    @property
    def summary(self) -> str:
        parts = [cancelled_meal_summary(self.name) if self.is_cancelled else self.name]
        if self.child_name:
            parts.append(self.child_name)
        if self.status != MEAL_STATUS_UNKNOWN:
            parts.append(self.status)
        return " - ".join(parts)

    @property
    def end_date(self) -> date:
        return self.date + timedelta(days=1)

    def as_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "date": self.date.isoformat(),
            "name": self.name,
            "meal_type": self.meal_type,
            "can_cancel": self.can_cancel,
            "is_cancelled": self.is_cancelled,
            "status": self.status,
        }
        if self.menu:
            attributes["menu"] = self.menu
        if self.meal_id:
            attributes["meal_id"] = self.meal_id
        if self.child_id:
            attributes["child_id"] = self.child_id
        if self.child_name:
            attributes["child_name"] = self.child_name
        if self.order_number:
            attributes["order_number"] = self.order_number
        if self.price is not None:
            attributes["price"] = str(self.price)
        return attributes


@dataclass(frozen=True, slots=True)
class StartEduChild:
    """StartEdu child account represented as a Home Assistant device."""

    child_id: str
    name: str
    meals: tuple[StartEduMeal, ...] = ()
    current_month_order_status: str = MEAL_STATUS_UNKNOWN
    next_month_order_status: str = MEAL_STATUS_UNKNOWN
    next_month_ordering_available: bool | None = None
    next_order_opening_date: date | None = None
    current_order_number: str | None = None
    refund_available: Decimal | None = None
    unpaid_amount: Decimal | None = None

    @property
    def next_meal(self) -> StartEduMeal | None:
        today = datetime.now().date()
        upcoming = [
            meal
            for meal in self.meals
            if meal.date >= today and meal.status != MEAL_STATUS_NO_SCHOOL
        ]
        active = [meal for meal in upcoming if not meal.is_cancelled]
        return min(active or upcoming, key=lambda meal: meal.date, default=None)


@dataclass(frozen=True, slots=True)
class StartEduAccountData:
    """Snapshot of account data returned by StartEdu."""

    fetched_at: datetime
    children: tuple[StartEduChild, ...] = ()
    meals: tuple[StartEduMeal, ...] = ()
    active_child_id: str | None = None
    balance: Decimal | None = None
    refunds: Decimal | None = None

    @property
    def child_accounts(self) -> tuple[StartEduChild, ...]:
        if self.children:
            return self.children
        if not self.meals:
            return ()

        grouped: dict[tuple[str, str], list[StartEduMeal]] = {}
        for meal in self.meals:
            child_id = meal.child_id or meal.child_name or "default"
            child_name = meal.child_name or "StartEdu"
            grouped.setdefault((child_id, child_name), []).append(meal)

        return tuple(
            StartEduChild(child_id=child_id, name=child_name, meals=tuple(meals))
            for (child_id, child_name), meals in grouped.items()
        )

    @property
    def next_meal(self) -> StartEduMeal | None:
        today = self.fetched_at.date()
        upcoming = [
            meal
            for child in self.child_accounts
            for meal in child.meals
            if meal.date >= today
            and not meal.is_cancelled
            and meal.status != MEAL_STATUS_NO_SCHOOL
        ]
        if not upcoming:
            upcoming = [
                meal
                for child in self.child_accounts
                for meal in child.meals
                if meal.date >= today and meal.status != MEAL_STATUS_NO_SCHOOL
            ]
        return min(upcoming, key=lambda meal: meal.date, default=None)
