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

from custom_components.startedu.client import extract_login_form, parse_account_html


class StartEduClientParserTests(unittest.TestCase):
    def test_parse_account_html_fixture(self) -> None:
        html = Path("tests/fixtures/startedu_dashboard.html").read_text(encoding="utf-8")
        data = parse_account_html(html, datetime(2026, 5, 25, tzinfo=timezone.utc))

        self.assertEqual(data.balance, Decimal("123.45"))
        self.assertEqual(data.refunds, Decimal("5.00"))
        self.assertEqual(len(data.meals), 2)
        self.assertEqual(data.meals[0].name, "Lunch")
        self.assertEqual(data.meals[0].child_name, "Ada Example")
        self.assertEqual(data.meals[0].status, "ordered")
        self.assertEqual(data.meals[0].price, Decimal("12.50"))
        self.assertEqual(data.meals[1].name, "Soup")
        self.assertTrue(data.meals[1].is_cancelled)
        self.assertEqual(data.next_meal, data.meals[0])

    def test_extract_login_form_detects_credentials_fields(self) -> None:
        html = """
        <form action="/login" method="post">
          <input type="hidden" name="csrf" value="token">
          <input type="text" name="Login" placeholder="E-mail, login, or student number">
          <input type="password" name="Password">
        </form>
        """

        form = extract_login_form(html)

        self.assertEqual(form.action, "/login")
        self.assertEqual(form.method, "post")
        self.assertEqual(form.fields["csrf"], "token")
        self.assertEqual(form.login_field, "Login")
        self.assertEqual(form.password_field, "Password")
