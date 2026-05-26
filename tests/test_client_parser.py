from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

startedu = types.ModuleType("custom_components.startedu")
startedu.__path__ = [str(ROOT / "custom_components" / "startedu")]
sys.modules.setdefault("custom_components.startedu", startedu)

from custom_components.startedu.client import (
    extract_login_form,
    parse_account_html,
    parse_commitments_html,
    parse_dashboard_html,
    parse_order_html,
    parse_refunds_html,
)


class StartEduClientParserTests(unittest.TestCase):
    def test_parse_account_html_fixture(self) -> None:
        html = Path("tests/fixtures/startedu_dashboard.html").read_text(
            encoding="utf-8"
        )
        data = parse_account_html(html, datetime(2026, 5, 25, tzinfo=timezone.utc))

        self.assertEqual(data.balance, Decimal("123.45"))
        self.assertEqual(data.refunds, Decimal("5.00"))
        self.assertEqual(len(data.meals), 2)
        self.assertEqual(data.meals[0].name, "Lunch")
        self.assertEqual(data.meals[0].child_name, "Ada Example")
        self.assertEqual(data.meals[0].status, "paid")
        self.assertEqual(data.meals[0].price, Decimal("12.50"))
        self.assertEqual(data.meals[1].name, "Soup")
        self.assertTrue(data.meals[1].is_cancelled)
        self.assertEqual(data.next_meal, data.meals[0])

    def test_extract_login_form_detects_credentials_fields(self) -> None:
        html = """
        <form action="/login" method="post">
          <input type="hidden" name="csrf" value="token">
          <input
            type="text"
            name="Login"
            placeholder="E-mail, login, or student number"
          >
          <input type="password" name="Password">
        </form>
        """

        form = extract_login_form(html)

        self.assertEqual(form.action, "/login")
        self.assertEqual(form.method, "post")
        self.assertEqual(form.fields["csrf"], "token")
        self.assertEqual(form.login_field, "Login")
        self.assertEqual(form.password_field, "Password")

    def test_parse_dashboard_html_extracts_child_and_order_state(self) -> None:
        html = Path(
            "tests/fixtures/startedu_client_dashboard_sanitized.html"
        ).read_text(encoding="utf-8")

        dashboard = parse_dashboard_html(html)

        self.assertEqual(dashboard.active_child_id, "CLIENT_ID_1")
        self.assertEqual(dashboard.active_child_name, "CHILD_1")
        self.assertEqual(len(dashboard.child_links), 2)
        self.assertEqual(dashboard.order_paths, ("/Order/Show/ORDER_ID",))
        self.assertEqual(dashboard.current_month_order_status, "paid")
        self.assertFalse(dashboard.next_month_ordering_available)
        self.assertEqual(dashboard.next_order_opening_date.isoformat(), "2026-05-25")

    def test_parse_order_html_extracts_meal_slots(self) -> None:
        html = Path("tests/fixtures/startedu_order_show_sanitized.html").read_text(
            encoding="utf-8"
        )

        meals = parse_order_html(
            html,
            "CLIENT_ID_1",
            "CHILD_1",
            "paid",
            order_id="ORDER_ID",
        )

        self.assertEqual(len(meals), 6)
        self.assertEqual(meals[0].status, "no_school")
        self.assertEqual(meals[1].name, "Obiad")
        self.assertEqual(meals[1].meal_type, "lunch")
        self.assertEqual(meals[1].price, Decimal("20.50"))
        self.assertEqual(meals[2].name, "Podwieczorek")
        self.assertEqual(meals[3].status, "cancelled")
        self.assertTrue(meals[4].can_cancel)
        self.assertTrue(meals[5].can_cancel)
        self.assertEqual(meals[4].raw["order_id"], "ORDER_ID")
        self.assertEqual(meals[4].raw["day_number"], 26)
        self.assertTrue(meals[4].raw["can_cancel_action"])
        self.assertTrue(meals[3].raw["cancel_marker"])

    def test_parse_refunds_and_commitments_html(self) -> None:
        refunds_html = Path("tests/fixtures/startedu_refunds_sanitized.html").read_text(
            encoding="utf-8"
        )
        commitments_html = Path(
            "tests/fixtures/startedu_commitments_sanitized.html"
        ).read_text(encoding="utf-8")

        self.assertEqual(parse_refunds_html(refunds_html), Decimal("20.50"))
        self.assertEqual(parse_commitments_html(commitments_html), Decimal("0.00"))
