from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest

from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()

from custom_components.startedu import binary_sensor, calendar, sensor
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
        tomorrow_status = _entity_by_key(entities, "tomorrow_meal_status")
        next_meal = _entity_by_key(entities, "next_meal")
        last_update = _entity_by_key(entities, "last_successful_update")
        current_month = _entity_by_key(entities, "current_month_order_status")
        next_month = _entity_by_key(entities, "next_month_order_status")
        next_opening = _entity_by_key(entities, "next_order_opening_date")
        refund = _entity_by_key(entities, "refund_available")
        unpaid = _entity_by_key(entities, "unpaid_amount")

        self.assertEqual(
            today_menu.native_value,
            "Obiad: Rosół. Kotlet. Kompot.; Podwieczorek: Jabłko.",
        )
        self.assertEqual(today_status.native_value, MEAL_STATUS_PAID)
        self.assertEqual(tomorrow_status.native_value, MEAL_STATUS_CANCELLED)
        self.assertEqual(next_meal.native_value, "Obiad")
        self.assertEqual(
            last_update.native_value,
            datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(current_month.native_value, "ordered")
        self.assertEqual(next_month.native_value, "open")
        self.assertEqual(next_opening.native_value, date(2026, 6, 15))
        self.assertEqual(refund.native_value, Decimal("12.50"))
        self.assertIsNone(unpaid.native_value)

        attributes = today_menu.extra_state_attributes
        next_meal_attributes = next_meal.extra_state_attributes

        self.assertIsNotNone(attributes)
        self.assertIsNotNone(next_meal_attributes)
        self.assertEqual(attributes["date"], "2026-05-26")
        self.assertEqual(attributes["status"], MEAL_STATUS_PAID)
        self.assertEqual(attributes["order_number"], "ORDER-2026-05")
        self.assertEqual(len(attributes["meal_slots"]), 2)
        self.assertNotIn("meal_id", attributes["meal_slots"][0])
        self.assertNotIn("child_id", attributes["meal_slots"][0])
        self.assertEqual(next_meal_attributes["date"], "2026-05-26")
        self.assertEqual(next_meal_attributes["name"], "Obiad")
        self.assertEqual(next_meal_attributes["menu"], "Rosół. Kotlet. Kompot.")
        self.assertEqual(next_meal_attributes["meal_type"], MEAL_TYPE_LUNCH)
        self.assertEqual(next_meal_attributes["child"], "Child 1")
        self.assertEqual(next_meal_attributes["status"], MEAL_STATUS_PAID)
        self.assertEqual(next_meal_attributes["order_number"], "ORDER-2026-05")
        self.assertEqual(next_meal_attributes["price"], "20.50")
        self.assertTrue(next_meal_attributes["can_cancel"])

    async def test_binary_sensor_setup_exposes_read_only_flags(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(_account_data(child), entry)
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
        entities = []

        await binary_sensor.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(len(entities), len(binary_sensor.BINARY_SENSOR_DESCRIPTIONS))
        self.assertTrue(_entity_by_key(entities, "has_food_today").is_on)
        self.assertFalse(_entity_by_key(entities, "has_food_tomorrow").is_on)
        self.assertTrue(_entity_by_key(entities, "can_cancel_today_meal").is_on)
        self.assertFalse(_entity_by_key(entities, "can_cancel_tomorrow_meal").is_on)

    async def test_multi_child_sensor_setup_creates_entities_per_child(self) -> None:
        first = _child_with_meals()
        second = StartEduChild(child_id="CHILD-ID-2", name="Child 2", meals=())
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(
            StartEduAccountData(
                fetched_at=datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
                children=(first, second),
            ),
            entry,
        )
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
        entities = []

        await sensor.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(len(entities), 2 * len(sensor.SENSOR_DESCRIPTIONS))
        second_next_meal = next(
            entity
            for entity in entities
            if entity._child.child_id == "CHILD-ID-2"
            and entity.entity_description.key == "next_meal"
        )
        self.assertIsNone(second_next_meal.native_value)
        self.assertIsNone(second_next_meal.extra_state_attributes)


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
