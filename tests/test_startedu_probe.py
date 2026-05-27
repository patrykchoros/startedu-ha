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
from scripts.startedu_probe import build_probe_report, format_probe_report


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

