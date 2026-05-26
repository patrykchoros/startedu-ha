from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest

from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()

from custom_components.startedu import calendar, sensor
from custom_components.startedu.const import CONF_LUNCH_TIME, DOMAIN
from custom_components.startedu.models import (
    MEAL_STATUS_CANCELLED,
    MEAL_STATUS_PAID,
    MEAL_TYPE_AFTERNOON_SNACK,
    MEAL_TYPE_LUNCH,
    StartEduAccountData,
    StartEduChild,
    StartEduMeal,
)


class FakeConfigEntry:
    entry_id = "entry-id"

    def __init__(self, options: dict[str, object] | None = None) -> None:
        self.options = options or {}


class FakeCoordinator:
    def __init__(self, data: StartEduAccountData, entry: FakeConfigEntry) -> None:
        self.data = data
        self.entry = entry


class EntityTests(unittest.IsolatedAsyncioTestCase):
    async def test_calendar_setup_and_events_use_sanitized_meals(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry({CONF_LUNCH_TIME: "12:15"})
        coordinator = FakeCoordinator(_account_data(child), entry)
        hass = SimpleNamespace(
            data={DOMAIN: {entry.entry_id: coordinator}},
            config=SimpleNamespace(language="pl"),
        )
        entities = []

        await calendar.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(len(entities), 1)
        events = await entities[0].async_get_events(
            hass,
            date(2026, 5, 26),
            date(2026, 5, 28),
        )

        self.assertEqual(
            [event.summary for event in events],
            ["Obiad", "Podwieczorek", "ODWOŁANE: Obiad"],
        )
        self.assertEqual(events[0].start.isoformat(), "2026-05-26T12:15:00")
        self.assertIn("Status: paid", events[0].description)
        self.assertIn("Status: cancelled", events[2].description)

    async def test_sensor_setup_exposes_state_and_attributes(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(_account_data(child), entry)
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
        entities = []

        await sensor.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(len(entities), len(sensor.SENSOR_DESCRIPTIONS))

        today_menu = _entity_by_key(entities, "today_menu")
        today_status = _entity_by_key(entities, "today_meal_status")
        last_update = _entity_by_key(entities, "last_successful_update")
        refund = _entity_by_key(entities, "refund_available")

        self.assertEqual(
            today_menu.native_value,
            "Obiad: Rosół. Kotlet. Kompot.; Podwieczorek: Jabłko.",
        )
        self.assertEqual(today_status.native_value, MEAL_STATUS_PAID)
        self.assertEqual(
            last_update.native_value,
            datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(refund.native_value, Decimal("12.50"))

        attributes = today_menu.extra_state_attributes

        self.assertIsNotNone(attributes)
        self.assertEqual(attributes["date"], "2026-05-26")
        self.assertEqual(attributes["status"], MEAL_STATUS_PAID)
        self.assertEqual(attributes["order_number"], "ORDER-2026-05")
        self.assertEqual(len(attributes["meal_slots"]), 2)
        self.assertEqual(attributes["meal_slots"][0]["meal_id"], "MEAL-26-LUNCH")


def _child_with_meals() -> StartEduChild:
    return StartEduChild(
        child_id="CHILD-ID-1",
        name="Child 1",
        current_month_order_status="ordered",
        next_month_order_status="open",
        refund_available=Decimal("12.50"),
        unpaid_amount=None,
        next_order_opening_date=date(2026, 6, 15),
        meals=(
            StartEduMeal(
                meal_id="MEAL-26-LUNCH",
                date=date(2026, 5, 26),
                name="Obiad",
                menu="Rosół. Kotlet. Kompot.",
                meal_type=MEAL_TYPE_LUNCH,
                child_id="CHILD-ID-1",
                child_name="Child 1",
                status=MEAL_STATUS_PAID,
                order_number="ORDER-2026-05",
                price=Decimal("20.50"),
                can_cancel=True,
            ),
            StartEduMeal(
                meal_id="MEAL-26-SNACK",
                date=date(2026, 5, 26),
                name="Podwieczorek",
                menu="Jabłko.",
                meal_type=MEAL_TYPE_AFTERNOON_SNACK,
                child_id="CHILD-ID-1",
                child_name="Child 1",
                status=MEAL_STATUS_PAID,
                order_number="ORDER-2026-05",
                price=Decimal("5.00"),
                can_cancel=True,
            ),
            StartEduMeal(
                meal_id="MEAL-27-LUNCH",
                date=date(2026, 5, 27),
                name="Obiad",
                menu="Naleśniki.",
                meal_type=MEAL_TYPE_LUNCH,
                child_id="CHILD-ID-1",
                child_name="Child 1",
                status=MEAL_STATUS_CANCELLED,
                order_number="ORDER-2026-05",
                price=Decimal("20.50"),
                can_cancel=False,
            ),
        ),
    )


def _account_data(child: StartEduChild) -> StartEduAccountData:
    return StartEduAccountData(
        fetched_at=datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
        children=(child,),
    )


def _entity_by_key(entities: list[object], key: str):
    return next(entity for entity in entities if entity.entity_description.key == key)
