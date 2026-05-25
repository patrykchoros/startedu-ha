from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class StartEduMeal:
    """A single meal entry exposed by StartEdu."""

    meal_id: str | None
    date: date
    name: str
    child_name: str | None = None
    status: str | None = None
    price: Decimal | None = None
    can_cancel: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_cancelled(self) -> bool:
        if self.status is None:
            return False
        status = self.status.casefold()
        return "cancel" in status or "odwol" in status or "odwo" in status

    @property
    def summary(self) -> str:
        parts = [self.name]
        if self.child_name:
            parts.append(self.child_name)
        if self.status:
            parts.append(self.status)
        return " - ".join(parts)

    @property
    def end_date(self) -> date:
        return self.date + timedelta(days=1)

    def as_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "date": self.date.isoformat(),
            "name": self.name,
            "can_cancel": self.can_cancel,
            "is_cancelled": self.is_cancelled,
        }
        if self.meal_id:
            attributes["meal_id"] = self.meal_id
        if self.child_name:
            attributes["child_name"] = self.child_name
        if self.status:
            attributes["status"] = self.status
        if self.price is not None:
            attributes["price"] = str(self.price)
        return attributes


@dataclass(frozen=True, slots=True)
class StartEduAccountData:
    """Snapshot of account data returned by StartEdu."""

    fetched_at: datetime
    meals: tuple[StartEduMeal, ...] = ()
    balance: Decimal | None = None
    refunds: Decimal | None = None

    @property
    def next_meal(self) -> StartEduMeal | None:
        today = self.fetched_at.date()
        upcoming = [
            meal for meal in self.meals if meal.date >= today and not meal.is_cancelled
        ]
        if not upcoming:
            upcoming = [meal for meal in self.meals if meal.date >= today]
        return min(upcoming, key=lambda meal: meal.date, default=None)
