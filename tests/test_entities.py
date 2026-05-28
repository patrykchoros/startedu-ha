from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest

from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()

from homeassistant.exceptions import HomeAssistantError

from custom_components.startedu import binary_sensor, button, calendar, sensor
from custom_components.startedu.client import MealCancellationNotAllowed
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
        self.hass = None
        self.sync_activity = "waiting"
        self.last_sync_status = "successful"
        self.last_sync_time = datetime(2026, 5, 26, 8, 15, tzinfo=timezone.utc)
        self.cancel_calls: list[tuple[str, date]] = []
        self.cancel_error: Exception | None = None
        self.refresh_calls = 0

    async def async_cancel_meal(self, child_id: str, target_date: date) -> None:
        if self.cancel_error is not None:
            raise self.cancel_error
        self.cancel_calls.append((child_id, target_date))

    async def async_request_refresh(self) -> None:
        self.refresh_calls += 1


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
        current_event = entities[0].event
        self.assertIsNotNone(current_event)
        self.assertEqual(current_event.summary, "Obiad")
        self.assertIsNotNone(current_event.start.tzinfo)

        events = await entities[0].async_get_events(
            hass,
            date(2026, 5, 26),
            date(2026, 5, 28),
        )

        self.assertEqual(
            [event.summary for event in events],
            ["Obiad", "Podwieczorek", "ODWOŁANE: Obiad"],
        )
        self.assertEqual(events[0].start.isoformat(), "2026-05-26T12:15:00+00:00")
        self.assertIsNotNone(events[0].start.tzinfo)
        self.assertIsNotNone(events[0].end.tzinfo)
        self.assertEqual(events[0].description, "Rosół. Kotlet. Kompot.")
        self.assertEqual(events[2].description, "Naleśniki.")
        self.assertNotIn("Status:", events[0].description or "")

        coordinator.data = _account_data(_child_after_refresh())
        refreshed_events = await entities[0].async_get_events(
            hass,
            date(2026, 5, 26),
            date(2026, 5, 27),
        )

        self.assertEqual(
            [event.summary for event in refreshed_events],
            ["ODWOŁANE: Obiad", "ODWOŁANE: Podwieczorek"],
        )

    async def test_sensor_setup_exposes_state_and_attributes(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(_account_data(child), entry)
        hass = SimpleNamespace(
            data={DOMAIN: {entry.entry_id: coordinator}},
            config=SimpleNamespace(language="pl"),
        )
        coordinator.hass = hass
        entities = []

        await sensor.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(
            len(entities),
            len(sensor.ACCOUNT_SENSOR_DESCRIPTIONS) + len(sensor.SENSOR_DESCRIPTIONS),
        )
        self.assertTrue(
            all(
                entity.entity_description.translation_placeholders is None
                for entity in entities
            )
        )
        self.assertTrue(
            all(
                entity.entity_description.entity_registry_enabled_default
                for entity in entities
            )
        )

        today_menu = _entity_by_key(entities, "today_menu")
        sync_status = _entity_by_key(entities, "sync_status")
        last_sync_status = _entity_by_key(entities, "last_sync_status")
        last_sync_time = _entity_by_key(entities, "last_sync_time")
        today_status = _entity_by_key(entities, "today_meal_status")
        tomorrow_status = _entity_by_key(entities, "tomorrow_meal_status")
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
        self.assertEqual(sync_status.native_value, "oczekuje")
        self.assertEqual(last_sync_status.native_value, "udane")
        self.assertEqual(
            last_sync_time.native_value,
            datetime(2026, 5, 26, 8, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(today_status.native_value, "opłacone")
        self.assertEqual(tomorrow_status.native_value, "odwołane")
        self.assertEqual(
            last_update.native_value,
            datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(current_month.native_value, "opłacone")
        self.assertEqual(next_month.native_value, "dostępne")
        self.assertEqual(next_opening.native_value, date(2026, 6, 15))
        self.assertEqual(refund.native_value, Decimal("12.50"))
        self.assertIsNone(unpaid.native_value)
        self.assertIsNone(refund.entity_description.suggested_unit_of_measurement)

        attributes = today_menu.extra_state_attributes

        self.assertIsNotNone(attributes)
        self.assertEqual(attributes["date"], "2026-05-26")
        self.assertEqual(attributes["status"], "opłacone")
        self.assertEqual(attributes["status_code"], MEAL_STATUS_PAID)
        self.assertEqual(attributes["order_number"], "ORDER-2026-05")
        self.assertEqual(len(attributes["meal_slots"]), 2)
        self.assertNotIn("meal_id", attributes["meal_slots"][0])
        self.assertNotIn("child_id", attributes["meal_slots"][0])
        self.assertEqual(attributes["meal_slots"][0]["menu"], "Rosół. Kotlet. Kompot.")
        self.assertEqual(attributes["meal_slots"][0]["status"], "opłacone")
        self.assertEqual(attributes["meal_slots"][0]["status_code"], MEAL_STATUS_PAID)

        coordinator.data = _account_data(_child_after_refresh())
        coordinator.sync_activity = "running"
        coordinator.last_sync_status = "failed"

        self.assertEqual(sync_status.native_value, "w toku")
        self.assertEqual(last_sync_status.native_value, "nieudane")
        self.assertEqual(today_status.native_value, "odwołane")
        self.assertEqual(today_menu.extra_state_attributes["status"], "odwołane")
        self.assertEqual(
            today_menu.extra_state_attributes["status_code"],
            MEAL_STATUS_CANCELLED,
        )
        self.assertEqual(next_month.native_value, "opłacone")
        self.assertEqual(unpaid.native_value, Decimal("7.50"))

    async def test_binary_sensor_setup_exposes_read_only_flags(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(_account_data(child), entry)
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
        entities = []

        await binary_sensor.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(len(entities), len(binary_sensor.BINARY_SENSOR_DESCRIPTIONS))
        self.assertTrue(
            all(
                entity.entity_description.translation_placeholders is None
                for entity in entities
            )
        )
        self.assertTrue(
            all(
                entity.entity_description.entity_registry_enabled_default
                for entity in entities
            )
        )
        self.assertTrue(
            all(entity.entity_description.device_class is None for entity in entities)
        )
        self.assertTrue(_entity_by_key(entities, "has_food_today").is_on)
        self.assertFalse(_entity_by_key(entities, "has_food_tomorrow").is_on)
        self.assertTrue(_entity_by_key(entities, "can_cancel_today_meal").is_on)
        self.assertFalse(_entity_by_key(entities, "can_cancel_tomorrow_meal").is_on)

        coordinator.data = _account_data(_child_after_refresh())

        self.assertFalse(_entity_by_key(entities, "has_food_today").is_on)
        self.assertFalse(_entity_by_key(entities, "can_cancel_today_meal").is_on)
        self.assertFalse(
            _entity_by_key(entities, "next_month_ordering_available").is_on
        )

    async def test_button_setup_exposes_refresh_and_cancel_buttons(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(_account_data(child), entry)
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
        entities = []

        await button.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(
            len(entities),
            1 + len(button.CANCEL_MEAL_BUTTON_DESCRIPTIONS),
        )
        refresh = _entity_by_translation_key(entities, "refresh_startedu_data")
        cancel_today = _entity_by_key(entities, "cancel_today_meals")
        cancel_tomorrow = _entity_by_key(entities, "cancel_tomorrow_meals")

        self.assertTrue(cancel_today.available)
        self.assertFalse(cancel_tomorrow.available)

        await refresh.async_press()
        await cancel_today.async_press()

        self.assertEqual(coordinator.refresh_calls, 1)
        self.assertEqual(
            coordinator.cancel_calls,
            [("CHILD-ID-1", date(2026, 5, 26))],
        )

        coordinator.data = _account_data(_child_after_refresh())

        self.assertFalse(cancel_today.available)
        with self.assertRaises(HomeAssistantError):
            await cancel_today.async_press()

    async def test_cancel_button_wraps_stale_startedu_rejection(self) -> None:
        child = _child_with_meals()
        entry = FakeConfigEntry()
        coordinator = FakeCoordinator(_account_data(child), entry)
        coordinator.cancel_error = MealCancellationNotAllowed("missing_cancel_action")
        hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
        entities = []

        await button.async_setup_entry(hass, entry, entities.extend)

        cancel_today = _entity_by_key(entities, "cancel_today_meals")
        self.assertTrue(cancel_today.available)
        with self.assertRaises(HomeAssistantError):
            await cancel_today.async_press()

    async def test_cancel_buttons_are_isolated_per_child(self) -> None:
        first = _child_with_meals()
        second = StartEduChild(
            child_id="CHILD-ID-2",
            name="Child 2",
            meals=(
                StartEduMeal(
                    meal_id="MEAL-26-LUNCH-2",
                    date=date(2026, 5, 26),
                    name="Obiad",
                    meal_type=MEAL_TYPE_LUNCH,
                    child_id="CHILD-ID-2",
                    child_name="Child 2",
                    status=MEAL_STATUS_PAID,
                    can_cancel=True,
                ),
            ),
        )
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

        await button.async_setup_entry(hass, entry, entities.extend)

        self.assertEqual(5, len(entities))
        second_today = _entity_by_unique_id(
            entities,
            "entry-id_CHILD-ID-2_cancel_today_meals",
        )

        await second_today.async_press()

        self.assertEqual(
            coordinator.cancel_calls,
            [("CHILD-ID-2", date(2026, 5, 26))],
        )

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

        self.assertEqual(
            len(entities),
            len(sensor.ACCOUNT_SENSOR_DESCRIPTIONS)
            + 2 * len(sensor.SENSOR_DESCRIPTIONS),
        )
        self.assertFalse(
            any(entity.entity_description.key == "next_meal" for entity in entities)
        )


def _child_with_meals() -> StartEduChild:
    return StartEduChild(
        child_id="CHILD-ID-1",
        name="Child 1",
        current_month_order_status="paid",
        next_month_order_status="available",
        refund_available=Decimal("12.50"),
        unpaid_amount=None,
        next_order_opening_date=date(2026, 6, 15),
        meals=(
            StartEduMeal(
                meal_id="MEAL-26-LUNCH",
                date=date(2026, 5, 26),
                name="Obiad",
                menu="ROSÓŁ. KOTLET. KOMPOT.",
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
                menu="jabłko.",
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


def _child_after_refresh() -> StartEduChild:
    return StartEduChild(
        child_id="CHILD-ID-1",
        name="Child 1",
        current_month_order_status="paid",
        next_month_order_status="paid",
        next_month_ordering_available=False,
        refund_available=Decimal("12.50"),
        unpaid_amount=Decimal("7.50"),
        meals=(
            StartEduMeal(
                meal_id="MEAL-26-LUNCH",
                date=date(2026, 5, 26),
                name="Obiad",
                menu="ROSÓŁ. KOTLET. KOMPOT.",
                meal_type=MEAL_TYPE_LUNCH,
                child_id="CHILD-ID-1",
                child_name="Child 1",
                status=MEAL_STATUS_CANCELLED,
                order_number="ORDER-2026-05",
                price=Decimal("20.50"),
                can_cancel=False,
            ),
            StartEduMeal(
                meal_id="MEAL-26-SNACK",
                date=date(2026, 5, 26),
                name="Podwieczorek",
                menu="jabłko.",
                meal_type=MEAL_TYPE_AFTERNOON_SNACK,
                child_id="CHILD-ID-1",
                child_name="Child 1",
                status=MEAL_STATUS_CANCELLED,
                order_number="ORDER-2026-05",
                price=Decimal("5.00"),
                can_cancel=False,
            ),
            StartEduMeal(
                meal_id="MEAL-01-LUNCH",
                date=date(2026, 6, 1),
                name="Obiad",
                menu="Zupa.",
                meal_type=MEAL_TYPE_LUNCH,
                child_id="CHILD-ID-1",
                child_name="Child 1",
                status=MEAL_STATUS_PAID,
                order_number="ORDER-2026-06",
                price=Decimal("20.50"),
                can_cancel=True,
            ),
        ),
    )


def _account_data(child: StartEduChild) -> StartEduAccountData:
    return StartEduAccountData(
        fetched_at=datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
        children=(child,),
    )


def _entity_by_key(entities: list[object], key: str):
    return next(
        entity
        for entity in entities
        if getattr(getattr(entity, "entity_description", None), "key", None) == key
    )


def _entity_by_unique_id(entities: list[object], unique_id: str):
    return next(entity for entity in entities if entity._attr_unique_id == unique_id)


def _entity_by_translation_key(entities: list[object], translation_key: str):
    return next(
        entity
        for entity in entities
        if getattr(entity, "_attr_translation_key", None) == translation_key
    )
