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
    meal_public_attributes,
    meal_time_window,
    next_child_meal,
    normalize_meal_label,
    normalize_menu_text,
)
from custom_components.startedu.models import (
    MEAL_STATUS_CANCELLED,
    MEAL_STATUS_NO_SCHOOL,
    StartEduChild,
    StartEduMeal,
)


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
                    menu="ROSÓŁ. KOTLET. KOMPOT.",
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
                    menu="tapioka.",
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
        self.assertEqual(
            meal_event_description(self.child.meals[0]),
            "Rosół. Kotlet. Kompot.",
        )

    def test_menu_text_is_normalized_to_natural_casing(self) -> None:
        self.assertEqual(
            normalize_menu_text("ZUPA POMIDOROWA. MAKARON Z SEREM."),
            "Zupa pomidorowa. Makaron z serem.",
        )
        self.assertEqual(
            normalize_menu_text("zupa pomidorowa. makaron z serem."),
            "Zupa pomidorowa. Makaron z serem.",
        )
        self.assertEqual(
            normalize_menu_text("Ryż BIO z warzywami."),
            "Ryż BIO z warzywami.",
        )
        self.assertEqual(
            normalize_menu_text(
                "ŻUREK, GULASZ STAROPOLSKI, KOPYTKA, "
                "SAŁATKA SZWEDZKA, KOMPOT / LEMONIADA"
            ),
            "Żurek, gulasz staropolski, kopytka, "
            "sałatka szwedzka, kompot / lemoniada",
        )
        self.assertEqual(
            normalize_menu_text("MANGO LASSI / CHRUPKI KUKURYDZIANE"),
            "Mango lassi / chrupki kukurydziane",
        )
        self.assertEqual(normalize_meal_label("OBIAD"), "Obiad")
        self.assertEqual(normalize_meal_label("podwieczorek"), "Podwieczorek")

    def test_cancelled_calendar_event_uses_localized_prefix(self) -> None:
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

        self.assertEqual(meal_event_summary(meal, "pl"), "ODWOŁANE: Obiad")
        self.assertEqual(meal_event_summary(meal, "en"), "CANCELLED: Obiad")
        self.assertEqual(meal_event_summary(meal, "en-US"), "CANCELLED: Obiad")
        self.assertEqual(meal_event_summary(meal, "de"), "CANCELLED: Obiad")
        self.assertEqual(meal.summary, "CANCELLED: Obiad - CHILD_1 - cancelled")

    def test_day_automation_helpers(self) -> None:
        self.assertTrue(has_food(self.child, self.today))
        self.assertTrue(can_cancel(self.child, self.today))
        self.assertEqual(day_status(self.child, self.today), "paid")

        state = day_menu_state(self.child, self.today, "pl")
        attributes = day_menu_attributes(self.child, self.today, "pl")

        self.assertIsNotNone(state)
        self.assertLessEqual(len(state or ""), 240)
        self.assertIn("Rosół. Kotlet. Kompot.", state or "")
        self.assertIn("full_menu", attributes)
        self.assertEqual(attributes["status"], "opłacone")
        self.assertEqual(attributes["status_code"], "paid")
        self.assertEqual(len(attributes["meal_slots"]), 2)
        self.assertNotIn("meal_id", attributes["meal_slots"][0])
        self.assertNotIn("child_id", attributes["meal_slots"][0])

    def test_day_menu_state_formats_itemized_menu_sections(self) -> None:
        child = StartEduChild(
            child_id="CLIENT_ID_1",
            name="CHILD_1",
            meals=(
                StartEduMeal(
                    meal_id=None,
                    date=self.today,
                    name="OBIAD",
                    menu=(
                        "ŻUREK, GULASZ STAROPOLSKI, KOPYTKA, "
                        "SAŁATKA SZWEDZKA, KOMPOT / LEMONIADA"
                    ),
                    meal_type="lunch",
                    status="paid",
                ),
                StartEduMeal(
                    meal_id=None,
                    date=self.today,
                    name="podwieczorek",
                    menu="MANGO LASSI / CHRUPKI KUKURYDZIANE",
                    meal_type="afternoon_snack",
                    status="paid",
                ),
            ),
        )

        self.assertEqual(
            day_menu_state(child, self.today, "pl"),
            "Obiad: Żurek, gulasz staropolski, kopytka, "
            "sałatka szwedzka, kompot / lemoniada; "
            "Podwieczorek: Mango lassi / chrupki kukurydziane",
        )
        self.assertEqual(
            meal_event_description(child.meals[0]),
            "Żurek, gulasz staropolski, kopytka, "
            "sałatka szwedzka, kompot / lemoniada",
        )

    def test_next_meal_prefers_active_meals_and_exposes_public_attributes(self) -> None:
        cancelled = StartEduMeal(
            meal_id="internal-meal-id",
            date=date(2026, 5, 27),
            name="Obiad",
            menu="Cancelled.",
            meal_type="lunch",
            child_id="internal-child-id",
            child_name="CHILD_1",
            status=MEAL_STATUS_CANCELLED,
            order_number="SE/ORDER_ID/5/2026",
            price=Decimal("20.50"),
        )
        active = StartEduMeal(
            meal_id="internal-meal-id-2",
            date=date(2026, 5, 28),
            name="Obiad",
            menu="Zupa.",
            meal_type="lunch",
            child_id="internal-child-id",
            child_name="CHILD_1",
            status="paid",
            order_number="SE/ORDER_ID/5/2026",
            price=Decimal("20.50"),
            can_cancel=True,
        )
        child = StartEduChild(
            child_id="internal-child-id",
            name="CHILD_1",
            meals=(cancelled, active),
        )

        meal = next_child_meal(child, date(2026, 5, 26))
        attributes = meal_public_attributes(active, "pl")

        self.assertIs(meal, active)
        self.assertEqual(attributes["date"], "2026-05-28")
        self.assertEqual(attributes["name"], "Obiad")
        self.assertEqual(attributes["menu"], "Zupa.")
        self.assertEqual(attributes["meal_type"], "lunch")
        self.assertEqual(attributes["child"], "CHILD_1")
        self.assertEqual(attributes["status"], "opłacone")
        self.assertEqual(attributes["status_code"], "paid")
        self.assertEqual(attributes["order_number"], "SE/ORDER_ID/5/2026")
        self.assertEqual(attributes["price"], "20.50")
        self.assertTrue(attributes["can_cancel"])
        self.assertNotIn("meal_id", attributes)
        self.assertNotIn("child_id", attributes)

    def test_empty_unavailable_and_cancelled_days(self) -> None:
        no_school_day = date(2026, 5, 27)
        cancelled_day = date(2026, 5, 28)
        child = StartEduChild(
            child_id="CLIENT_ID_1",
            name="CHILD_1",
            meals=(
                StartEduMeal(
                    meal_id=None,
                    date=no_school_day,
                    name="Brak zajęć",
                    meal_type="other",
                    status=MEAL_STATUS_NO_SCHOOL,
                ),
                StartEduMeal(
                    meal_id=None,
                    date=cancelled_day,
                    name="Obiad",
                    meal_type="lunch",
                    status=MEAL_STATUS_CANCELLED,
                ),
            ),
        )

        self.assertIsNone(day_menu_state(child, date(2026, 5, 26)))
        self.assertEqual(day_status(child, date(2026, 5, 26)), "unknown")
        self.assertIsNone(day_menu_state(child, no_school_day))
        self.assertEqual(day_status(child, no_school_day), "no_school")
        self.assertEqual(day_status(child, cancelled_day), "cancelled")
