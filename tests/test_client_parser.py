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
    InvalidAuth,
    StartEduClient,
    extract_login_form,
    parse_account_html,
    parse_commitments_html,
    parse_dashboard_html,
    parse_order_html,
    parse_refunds_html,
    safe_url_for_log,
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

    def test_extract_login_form_detects_startedu_identifier_field(self) -> None:
        html = Path("tests/fixtures/startedu_login_page_sanitized.html").read_text(
            encoding="utf-8"
        )

        form = extract_login_form(html)

        self.assertEqual(form.action, "/User/SignIn")
        self.assertEqual(form.login_field, "Identifier")
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


class StartEduLoginDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_login_adopts_response_shard_host(self) -> None:
        session = _LoginSession(
            get_responses=[
                _TextResponse(
                    Path("tests/fixtures/startedu_login_page_sanitized.html").read_text(
                        encoding="utf-8"
                    ),
                    url="https://s3.startedu.pl/Home/Client",
                )
            ],
            post_responses=[
                _TextResponse(
                    Path(
                        "tests/fixtures/startedu_client_dashboard_sanitized.html"
                    ).read_text(encoding="utf-8"),
                    url="https://s4.startedu.pl/Home/Client",
                )
            ],
        )
        client = StartEduClient(
            session,
            "family@example.test",
            "secret-password",
            base_url="https://s3.startedu.pl/Home/Client",
        )

        await client.async_login()

        self.assertEqual(
            client._base_url,
            "https://s4.startedu.pl/Home/Client/",
        )

    async def test_invalid_login_logs_only_safe_diagnostics(self) -> None:
        session = _LoginSession(
            get_responses=[
                _TextResponse(
                    Path("tests/fixtures/startedu_login_page_sanitized.html").read_text(
                        encoding="utf-8"
                    ),
                    url="https://startedu.pl/?redirect=%2fHome%2fClient",
                )
            ],
            post_responses=[
                _TextResponse(
                    Path(
                        "tests/fixtures/startedu_invalid_login_sanitized.html"
                    ).read_text(encoding="utf-8"),
                    url=(
                        "https://s1.startedu.pl/User/SignIn"
                        "?redirect=%2fHome%2fClient"
                    ),
                )
            ],
        )
        client = StartEduClient(
            session,
            "family@example.test",
            "secret-password",
            base_url="https://s3.startedu.pl/Home/Client",
        )

        with self.assertLogs("custom_components.startedu.client", "WARNING") as logs:
            with self.assertRaises(InvalidAuth):
                await client.async_login()

        logged = "\n".join(logs.output)
        self.assertIn("StartEdu login diagnostic", logged)
        self.assertIn("invalid_auth", logged)
        self.assertIn("base_url=https://s3.startedu.pl/Home/Client/", logged)
        self.assertIn("request_url=https://s3.startedu.pl/User/SignIn", logged)
        self.assertIn("response_url=https://s1.startedu.pl/User/SignIn", logged)
        self.assertIn("login_field=Identifier", logged)
        self.assertIn("password_field=Password", logged)
        self.assertNotIn("family@example.test", logged)
        self.assertNotIn("secret-password", logged)
        self.assertNotIn("redirect=", logged)
        self.assertNotIn("Logowanie nie powiodło", logged)

    def test_safe_url_for_log_drops_query_and_credentials(self) -> None:
        self.assertEqual(
            safe_url_for_log("https://user:pass@example.test/path?token=secret"),
            "https://example.test/path",
        )


class _LoginSession:
    def __init__(
        self,
        *,
        get_responses: list["_TextResponse"],
        post_responses: list["_TextResponse"],
    ) -> None:
        self.get_responses = get_responses
        self.post_responses = post_responses

    def get(self, url: str, **kwargs: object) -> "_TextResponse":
        return self.get_responses.pop(0)

    def post(self, url: str, **kwargs: object) -> "_TextResponse":
        return self.post_responses.pop(0)


class _TextResponse:
    def __init__(
        self,
        text: str,
        *,
        status: int = 200,
        url: str = "https://startedu.pl/",
    ) -> None:
        self._text = text
        self.status = status
        self.url = url

    async def __aenter__(self) -> "_TextResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        return self._text
