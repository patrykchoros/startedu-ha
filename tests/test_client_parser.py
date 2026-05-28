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
from custom_components.startedu.models import MEAL_STATUS_PAID, MEAL_STATUS_UNPAID


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
        self.assertEqual(dashboard.next_month_order_status, "blocked")
        self.assertEqual(dashboard.next_order_opening_date.isoformat(), "2026-05-25")

    def test_parse_dashboard_html_detects_available_next_order(self) -> None:
        html = """
        <html>
          <body>
            Subkonto | CHILD_1
            <section class="current-month">
              Zamówienie SE/ORDER_ID/5/2026 zostało opłacone.
              <a href="/Order/Show/ORDER_ID">Wyświetl</a>
            </section>
            <section class="next-month">
              <h2>Następny miesiąc: czerwiec</h2>
              <a href="/Order/Create">Złóż zamówienie</a>
            </section>
          </body>
        </html>
        """

        dashboard = parse_dashboard_html(html)

        self.assertTrue(dashboard.next_month_ordering_available)
        self.assertEqual(dashboard.next_month_order_status, "available")
        self.assertIsNone(dashboard.next_order_opening_date)

    def test_parse_dashboard_html_does_not_use_unrelated_dates_for_next_order(
        self,
    ) -> None:
        html = """
        <html>
          <body>
            Subkonto | CHILD_1
            <section class="current-month">
              Zamówienie SE/ORDER_ID/5/2026 zostało opłacone.
              <a href="/Order/Show/ORDER_ID">Wyświetl</a>
            </section>
            <footer>Regulamin obowiązuje od 25 maja 2018.</footer>
          </body>
        </html>
        """

        dashboard = parse_dashboard_html(html)

        self.assertEqual(dashboard.current_month_order_status, "paid")
        self.assertIsNone(dashboard.next_month_ordering_available)
        self.assertEqual(dashboard.next_month_order_status, "unknown")
        self.assertIsNone(dashboard.next_order_opening_date)

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

    def test_parse_order_html_accepts_day_attributes_in_any_order(self) -> None:
        html = """
        <html>
          <body>
            <h1>Zamówienie nr SE/ORDER_ID/5/2026 na maj 2026</h1>
            <div data-number='27' class='day green'>
              <h3>Obiad</h3>
              <p>Makaron.</p>
              <a data-action='cancel-meal' href='#'>Odwołaj posiłek</a>
            </div>
            <div data-number=28 class="day cancelled">
              <div>Rezygnacja</div>
              <h3>Podwieczorek</h3>
              <p>Owoc.</p>
            </div>
          </body>
        </html>
        """

        meals = parse_order_html(html, "CLIENT_ID_1", "CHILD_1", "paid")

        self.assertEqual([meal.date.isoformat() for meal in meals], [
            "2026-05-27",
            "2026-05-28",
        ])
        self.assertEqual(meals[0].name, "Obiad")
        self.assertTrue(meals[0].can_cancel)
        self.assertEqual(meals[1].status, "cancelled")

    def test_parse_order_html_extracts_title_based_meal_preview(self) -> None:
        html = """
        <html>
          <body>
            <h1>Zamówienie nr SE/ORDER_ID/5/2026 na maj 2026</h1>
            <div class="day green" data-number="27">
              <div class="meal-preview">
                <li class="title">Obiad</li>
                <ul>
                  <li>Zupa pomidorowa</li>
                  <li>Ryż z warzywami <span class="allergen-info">1</span></li>
                </ul>
                <li class="title">Podwieczorek</li>
                <ul><li>Jogurt</li></ul>
                <div class="price" data-price="20.50">Cena: 20,50 zł</div>
                <a data-action="cancel-meal" href="#">Odwołaj posiłek</a>
                <div class="allergens-legend">
                  <div class="label">1</div><div class="name">Gluten</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        meals = parse_order_html(html, "CLIENT_ID_1", "CHILD_1", "paid")

        self.assertEqual(len(meals), 2)
        self.assertEqual(meals[0].name, "Obiad")
        self.assertEqual(meals[0].menu, "Zupa pomidorowa, Ryż z warzywami")
        self.assertEqual(meals[1].name, "Podwieczorek")
        self.assertEqual(meals[1].menu, "Jogurt")
        self.assertTrue(all(meal.can_cancel for meal in meals))
        self.assertEqual(meals[0].price, Decimal("20.50"))

    def test_parse_order_html_preserves_menu_item_boundaries_and_variants(
        self,
    ) -> None:
        html = """
        <html>
          <body>
            <h1>Zamówienie nr SE/ORDER_ID/5/2026 na maj 2026</h1>
            <div class="day green" data-number="28">
              <ul class="meal-preview">
                <li class="title">OBIAD</li>
                <ul>
                  <li>ŻUREK</li>
                  <li>GULASZ STAROPOLSKI</li>
                  <li>KOPYTKA</li>
                  <li>SAŁATKA SZWEDZKA</li>
                  <li>KOMPOT / LEMONIADA</li>
                </ul>
                <li class="title">podwieczorek</li>
                <ul><li>MANGO LASSI / CHRUPKI KUKURYDZIANE</li></ul>
              </ul>
            </div>
          </body>
        </html>
        """

        meals = parse_order_html(html, "CLIENT_ID_1", "CHILD_1", MEAL_STATUS_PAID)

        self.assertEqual(
            meals[0].menu,
            "ŻUREK, GULASZ STAROPOLSKI, KOPYTKA, SAŁATKA SZWEDZKA, "
            "KOMPOT / LEMONIADA",
        )
        self.assertEqual(meals[1].menu, "MANGO LASSI / CHRUPKI KUKURYDZIANE")

    def test_parse_order_html_uses_order_page_status(self) -> None:
        html = """
        <html>
          <body>
            <h1>Zamówienie SE/ORDER_ID/6/2026 jest nieopłacone</h1>
            <div class="day green" data-number="1">
              <h3>Obiad</h3>
              <p>Zupa.</p>
            </div>
          </body>
        </html>
        """

        meals = parse_order_html(html, "CLIENT_ID_1", "CHILD_1", MEAL_STATUS_PAID)

        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0].status, MEAL_STATUS_UNPAID)

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
    async def test_child_switch_refreshes_dashboard_before_order_page(self) -> None:
        session = _LoginSession(
            get_responses=[
                _TextResponse(_order_html(), url="https://s4.startedu.pl/Order/Show/1"),
                _TextResponse("<html></html>", url="https://s4.startedu.pl/Refunds"),
                _TextResponse(
                    "<html></html>",
                    url="https://s4.startedu.pl/Commitments",
                ),
                _TextResponse(
                    "<html></html>",
                    url="https://s4.startedu.pl/User/SwitchClient/CLIENT_ID_2",
                ),
                _TextResponse(
                    _dashboard_html(active_child=2),
                    url="https://s4.startedu.pl/Home/Client",
                ),
                _TextResponse(_order_html(), url="https://s4.startedu.pl/Order/Show/2"),
                _TextResponse("<html></html>", url="https://s4.startedu.pl/Refunds"),
                _TextResponse(
                    "<html></html>",
                    url="https://s4.startedu.pl/Commitments",
                ),
            ],
            post_responses=[],
        )
        client = StartEduClient(
            session,
            "family@example.test",
            "secret-password",
            base_url="https://s4.startedu.pl/Home/Client",
        )
        client._authenticated = True
        client._last_html = _dashboard_html(active_child=1)

        data = await client.async_get_account_data()

        self.assertEqual(len(data.children), 2)
        self.assertEqual(
            session.get_urls[3],
            "https://s4.startedu.pl/User/SwitchClient/CLIENT_ID_2",
        )
        self.assertEqual(session.get_urls[4], "https://s4.startedu.pl/Home/Client")
        self.assertEqual(
            session.get_kwargs[4]["headers"]["Referer"],
            "https://s4.startedu.pl/User/SwitchClient/CLIENT_ID_2",
        )
        self.assertEqual(
            session.get_kwargs[5]["headers"]["Referer"],
            "https://s4.startedu.pl/Home/Client",
        )

    async def test_order_http_403_skips_order_page(self) -> None:
        session = _LoginSession(
            get_responses=[
                _TextResponse(
                    "",
                    status=403,
                    url="https://s1.startedu.pl/Order/Show/SECRET_ORDER",
                ),
                _TextResponse("<html></html>", url="https://s1.startedu.pl/Refunds"),
                _TextResponse(
                    "<html></html>",
                    url="https://s1.startedu.pl/Commitments",
                ),
            ],
            post_responses=[],
        )
        client = StartEduClient(
            session,
            "family@example.test",
            "secret-password",
            base_url="https://s1.startedu.pl/Home/Client",
        )
        client._authenticated = True
        client._last_html = """
        <html>
          <body>
            Subkonto | CHILD_1
            <a href="/Order/Show/SECRET_ORDER">Wyświetl</a>
          </body>
        </html>
        """

        with self.assertLogs("custom_components.startedu.client", "WARNING") as logs:
            data = await client.async_get_account_data()

        self.assertEqual(len(data.children), 1)
        self.assertEqual(data.children[0].meals, ())
        logged = "\n".join(logs.output)
        self.assertIn("skipped_order_page", logged)
        self.assertIn("partial_data", logged)
        self.assertIn("status=403", logged)
        self.assertIn("children=1", logged)
        self.assertIn("meals=0", logged)
        self.assertIn("skipped_order_pages=1", logged)
        self.assertIn("child_meal_counts=0", logged)
        self.assertIn("meal_dates=<empty>", logged)
        self.assertIn("/Order/Show/<redacted>", logged)
        self.assertNotIn("SECRET_ORDER", logged)
        self.assertEqual(
            session.get_kwargs[0]["headers"]["Referer"],
            "https://s1.startedu.pl/Home/Client",
        )
        self.assertIn("Mozilla/5.0", session.get_kwargs[0]["headers"]["User-Agent"])

    async def test_next_month_order_status_is_inferred_from_order_pages(self) -> None:
        session = _LoginSession(
            get_responses=[
                _TextResponse(
                    _month_order_html(order_id="CURRENT", month=5),
                    url="https://s4.startedu.pl/Order/Show/CURRENT",
                ),
                _TextResponse(
                    _month_order_html(order_id="NEXT", month=6),
                    url="https://s4.startedu.pl/Order/Show/NEXT",
                ),
                _TextResponse("<html></html>", url="https://s4.startedu.pl/Refunds"),
                _TextResponse(
                    "<html>Wszystkie zobowiązania są uregulowane</html>",
                    url="https://s4.startedu.pl/Commitments",
                ),
            ],
            post_responses=[],
        )
        client = StartEduClient(
            session,
            "family@example.test",
            "secret-password",
            base_url="https://s4.startedu.pl/Home/Client",
        )
        client._authenticated = True
        client._last_html = """
        <html>
          <body>
            Subkonto | CHILD_1
            <p>Zamówienie SE/CURRENT/5/2026 zostało opłacone.</p>
            <a href="/Order/Show/CURRENT">Wyświetl maj</a>
            <a href="/Order/Show/NEXT">Wyświetl czerwiec</a>
          </body>
        </html>
        """

        data = await client.async_get_account_data()
        child = data.children[0]

        self.assertEqual(child.current_month_order_status, MEAL_STATUS_PAID)
        self.assertEqual(child.next_month_order_status, MEAL_STATUS_PAID)
        self.assertFalse(child.next_month_ordering_available)
        self.assertEqual(
            sorted({meal.date.isoformat() for meal in child.meals}),
            ["2026-05-01", "2026-06-01"],
        )

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
        self.assertEqual(
            safe_url_for_log("https://s1.startedu.pl/Order/Show/SECRET?token=secret"),
            "https://s1.startedu.pl/Order/Show/<redacted>",
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
        self.get_urls: list[str] = []
        self.post_urls: list[str] = []
        self.get_kwargs: list[dict[str, object]] = []
        self.post_kwargs: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> "_TextResponse":
        self.get_urls.append(url)
        self.get_kwargs.append(dict(kwargs))
        return self.get_responses.pop(0)

    def post(self, url: str, **kwargs: object) -> "_TextResponse":
        self.post_urls.append(url)
        self.post_kwargs.append(dict(kwargs))
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


def _dashboard_html(*, active_child: int) -> str:
    first_class = "current" if active_child == 1 else ""
    second_class = "current" if active_child == 2 else ""
    order_id = f"ORDER_ID_{active_child}"
    child_name = f"CHILD_{active_child}"
    return f"""
    <html>
      <body>
        Subkonto | {child_name}
        <a class="{first_class}" href="/User/SwitchClient/CLIENT_ID_1">CHILD_1</a>
        <a class="{second_class}" href="/User/SwitchClient/CLIENT_ID_2">CHILD_2</a>
        <p>Zamówienie SE/{order_id}/5/2026 zostało opłacone.</p>
        <a href="/Order/Show/{order_id}">Wyświetl</a>
      </body>
    </html>
    """


def _order_html() -> str:
    return Path("tests/fixtures/startedu_order_show_sanitized.html").read_text(
        encoding="utf-8"
    )


def _month_order_html(*, order_id: str, month: int) -> str:
    return f"""
    <html>
      <body>
        <h1>Zamówienie SE/{order_id}/{month}/2026 zostało opłacone.</h1>
        <div class="day green" data-number="1">
          <h3>Obiad</h3>
          <p>Zupa.</p>
        </div>
      </body>
    </html>
    """
