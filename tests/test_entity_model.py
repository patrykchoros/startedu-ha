from __future__ import annotations

from datetime import date
from decimal import Decimal
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

startedu = types.ModuleType("custom_components.startedu")
startedu.__path__ = [str(ROOT / "custom_components" / "startedu")]
sys.modules.setdefault("custom_components.startedu", startedu)

from custom_components.startedu.entity_model import (
    can_cancel,
    day_menu_attributes,
    day_menu_state,
    day_status,
    has_food,
    meal_event_description,
    meal_event_summary,
    meal_time_window,
)
from custom_components.startedu.models import StartEduChild, StartEduMeal


class EntityModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = date(2026, 5, 26)
        self.child = StartEduChild(
            child_id="CLIENT_ID_1",
            name="CHILD_1",
            meals=(
                StartEduMeal(
                    meal_id="order-26-lunch",
                    date=self.today,
                    name="Obiad",
                    menu="Rosół. Kotlet. Kompot.",
                    meal_type="lunch",
                    child_id="CLIENT_ID_1",
                    child_name="CHILD_1",
                    status="paid",
                    order_number="SE/ORDER_ID/5/2026",
                    price=Decimal("20.50"),
                    can_cancel=True,
                ),
                StartEduMeal(
                    meal_id="order-26-snack",
                    date=self.today,
                    name="Podwieczorek",
                    menu="Tapioka.",
                    meal_type="afternoon_snack",
                    child_id="CLIENT_ID_1",
                    child_name="CHILD_1",
                    status="paid",
                    order_number="SE/ORDER_ID/5/2026",
                    price=Decimal("20.50"),
                    can_cancel=True,
                ),
            ),
        )

    def test_calendar_event_helpers_use_configured_times(self) -> None:
        window = meal_time_window(self.child.meals[0], {"lunch_time": "12:15"})

        self.assertEqual(window.start.isoformat(), "2026-05-26T12:15:00")
        self.assertEqual(window.end.isoformat(), "2026-05-26T13:00:00")
        self.assertEqual(meal_event_summary(self.child.meals[0]), "Obiad")
        self.assertIn("Rosół", meal_event_description(self.child.meals[0]))

    def test_cancelled_calendar_event_gets_prefix(self) -> None:
        meal = StartEduMeal(
            meal_id="order-18-lunch",
            date=date(2026, 5, 18),
            name="Obiad",
            menu="Cancelled menu.",
            meal_type="lunch",
            child_id="CLIENT_ID_1",
            child_name="CHILD_1",
            status="cancelled",
        )

        self.assertEqual(meal_event_summary(meal), "ODWOŁANE: Obiad")

    def test_day_automation_helpers(self) -> None:
        self.assertTrue(has_food(self.child, self.today))
        self.assertTrue(can_cancel(self.child, self.today))
        self.assertEqual(day_status(self.child, self.today), "paid")

        state = day_menu_state(self.child, self.today)
        attributes = day_menu_attributes(self.child, self.today)

        self.assertIsNotNone(state)
        self.assertLessEqual(len(state or ""), 240)
        self.assertIn("full_menu", attributes)
        self.assertEqual(len(attributes["meal_slots"]), 2)

