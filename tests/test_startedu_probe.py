from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
import unittest

from custom_components.startedu.models import (
    MEAL_STATUS_PAID,
    MEAL_TYPE_LUNCH,
    StartEduAccountData,
    StartEduChild,
    StartEduMeal,
)
from scripts.startedu_probe import (
    build_entity_report,
    build_probe_report,
    format_entity_report,
    format_probe_report,
)


class StartEduProbeTests(unittest.TestCase):
    def test_probe_report_is_sanitized_and_summarizes_meals(self) -> None:
        data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 27, 10, 0, tzinfo=timezone.utc),
            refunds=Decimal("12.50"),
            children=(
                StartEduChild(
                    child_id="SECRET_CHILD_ID_1",
                    name="Secret Child 1",
                    refund_available=Decimal("12.50"),
                    meals=(
                        StartEduMeal(
                            meal_id="SECRET_MEAL_ID",
                            date=date(2026, 5, 27),
                            name="Obiad",
                            meal_type=MEAL_TYPE_LUNCH,
                            status=MEAL_STATUS_PAID,
                            child_id="SECRET_CHILD_ID_1",
                            child_name="Secret Child 1",
                            can_cancel=True,
                        ),
                    ),
                ),
                StartEduChild(
                    child_id="SECRET_CHILD_ID_2",
                    name="Secret Child 2",
                    meals=(),
                ),
            ),
        )

        report = build_probe_report(data, today=date(2026, 5, 27))
        formatted = format_probe_report(report)
        serialized = json.dumps(report, ensure_ascii=False)

        self.assertEqual(report["children_count"], 2)
        self.assertEqual(report["total_meals"], 1)
        self.assertEqual(report["child_meal_counts"], [1, 0])
        self.assertEqual(report["meal_date_range"], "2026-05-27..2026-05-27")
        self.assertIn("child_without_meals", report["warnings"])
        self.assertEqual(report["children"][0]["today"]["status"], MEAL_STATUS_PAID)
        self.assertTrue(report["children"][0]["today"]["has_food"])
        self.assertTrue(report["children"][0]["today"]["can_cancel"])
        self.assertIn("child_meal_counts: 1,0", formatted)

        for secret in (
            "SECRET_CHILD_ID_1",
            "SECRET_CHILD_ID_2",
            "SECRET_MEAL_ID",
            "Secret Child",
        ):
            self.assertNotIn(secret, serialized)
            self.assertNotIn(secret, formatted)

    def test_entity_report_is_sanitized_and_covers_expected_entities(self) -> None:
        data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 27, 10, 0, tzinfo=timezone.utc),
            children=(
                StartEduChild(
                    child_id="SECRET_CHILD_ID_1",
                    name="Secret Child 1",
                    current_month_order_status="paid",
                    refund_available=Decimal("12.50"),
                    unpaid_amount=Decimal("0.00"),
                    meals=(
                        StartEduMeal(
                            meal_id="SECRET_MEAL_ID",
                            date=date(2026, 5, 27),
                            name="Obiad",
                            menu="Secret menu text",
                            meal_type=MEAL_TYPE_LUNCH,
                            status=MEAL_STATUS_PAID,
                            child_id="SECRET_CHILD_ID_1",
                            child_name="Secret Child 1",
                            can_cancel=True,
                        ),
                    ),
                ),
            ),
        )

        report = build_entity_report(data, today=date(2026, 5, 27))
        formatted = format_entity_report(report)
        serialized = json.dumps(report, ensure_ascii=False)
        child = report["children"][0]

        self.assertEqual(report["expected_entities"]["per_child"], 16)
        self.assertEqual(report["expected_entities"]["account"], 4)
        self.assertIn("sync_status", report["account_entities"])
        self.assertIn("last_sync_status", report["account_entities"])
        self.assertIn("last_sync_time", report["account_entities"])
        self.assertEqual(child["entity_count"], 16)
        self.assertTrue(child["sensors"]["today_menu"]["state_present"])
        self.assertEqual(child["sensors"]["today_menu"]["meal_slots"], 1)
        self.assertTrue(child["binary_sensors"]["has_food_today"])
        self.assertEqual(child["calendar"]["meals"]["events"], 1)
        self.assertIn("expected_entities: account=4 per_child=16", formatted)
        self.assertIn("account.sync_status: available=True", formatted)

        for secret in (
            "SECRET_CHILD_ID_1",
            "SECRET_MEAL_ID",
            "Secret Child",
            "Secret menu text",
        ):
            self.assertNotIn(secret, serialized)
            self.assertNotIn(secret, formatted)
