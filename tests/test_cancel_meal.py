from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

from ha_stubs import HomeAssistantError, ServiceCall, install_homeassistant_stubs

install_homeassistant_stubs()
sys.modules.pop("custom_components.startedu", None)

from custom_components.startedu import _async_handle_cancel_meal_service
from custom_components.startedu.client import (
    MealCancellationFailed,
    MealCancellationNotAllowed,
    StartEduClient,
    cancellation_confirmed,
    cancellation_target_from_data,
    parse_order_html,
)
from custom_components.startedu.const import (
    ATTR_CHILD_ID,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DATE,
    DOMAIN,
)
from custom_components.startedu.models import (
    MEAL_STATUS_CANCELLED,
    MEAL_STATUS_NO_SCHOOL,
    MEAL_STATUS_NOT_ORDERED,
    StartEduAccountData,
    StartEduChild,
    StartEduMeal,
)

DASHBOARD_HTML = """
<html>
  <body>
    <a class="current" href="/User/SwitchClient/CLIENT_ID_1">CHILD_1</a>
    <a href="/Order/Show/ORDER_ID">Zamówienie nr SE/ORDER_ID/5/2026</a>
    <p>Zamówienie zostało opłacone.</p>
  </body>
</html>
"""
REFUNDS_HTML = "<html><body>Zwroty: 0,00 zł</body></html>"
COMMITMENTS_HTML = "<html><body>Wszystkie zobowiązania są uregulowane.</body></html>"


class MealCancellationValidationTests(unittest.TestCase):
    def test_cancellation_target_requires_safe_preconditions(self) -> None:
        data = _account_data_from_order(_pre_cancel_order_html())

        target = cancellation_target_from_data(
            data,
            "CLIENT_ID_1",
            date(2026, 5, 26),
        )

        self.assertEqual(target.order_id, "ORDER_ID")
        self.assertEqual(target.day_number, 26)

        refusal_cases = (
            ("child_not_found", "OTHER_CHILD", date(2026, 5, 26)),
            ("day_missing", "CLIENT_ID_1", date(2026, 5, 31)),
            ("day_unavailable", "CLIENT_ID_1", date(2026, 5, 1)),
            ("already_cancelled", "CLIENT_ID_1", date(2026, 5, 18)),
            ("missing_cancel_action", "CLIENT_ID_1", date(2026, 5, 4)),
        )
        for reason, child_id, target_date in refusal_cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(MealCancellationNotAllowed, reason):
                    cancellation_target_from_data(data, child_id, target_date)

    def test_cancellation_target_rejects_not_ordered_day(self) -> None:
        data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
            children=(
                StartEduChild(
                    child_id="CLIENT_ID_1",
                    name="CHILD_1",
                    meals=(
                        StartEduMeal(
                            meal_id=None,
                            date=date(2026, 5, 26),
                            name="Obiad",
                            meal_type="lunch",
                            status=MEAL_STATUS_NOT_ORDERED,
                            raw={
                                "order_id": "ORDER_ID",
                                "day_number": 26,
                                "can_cancel_action": True,
                            },
                        ),
                    ),
                ),
            ),
        )

        with self.assertRaisesRegex(MealCancellationNotAllowed, "not_ordered"):
            cancellation_target_from_data(data, "CLIENT_ID_1", date(2026, 5, 26))

    def test_confirmation_requires_marker_and_no_cancel_action(self) -> None:
        confirmed = _account_data_from_order(_post_cancel_order_html())
        unconfirmed = _account_data_from_order(_pre_cancel_order_html())

        self.assertTrue(
            cancellation_confirmed(confirmed, "CLIENT_ID_1", date(2026, 5, 26))
        )
        self.assertFalse(
            cancellation_confirmed(unconfirmed, "CLIENT_ID_1", date(2026, 5, 26))
        )


class StartEduClientCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_posts_once_and_returns_confirmed_data(self) -> None:
        session = _session_for_cancel(_JsonResponse({"Status": True}))
        client = StartEduClient(
            session,
            "user",
            "password",
            base_url="https://s3.startedu.pl/Home/Client",
        )
        client._authenticated = True

        data = await client.async_cancel_meal("CLIENT_ID_1", date(2026, 5, 26))

        self.assertEqual(len(session.post_urls), 1)
        self.assertEqual(
            session.post_urls[0],
            "https://s3.startedu.pl/Order/CancelMeal?orderId=ORDER_ID&dayNumber=26",
        )
        self.assertEqual(
            session.post_kwargs[0]["headers"],
            {"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertTrue(
            cancellation_confirmed(data, "CLIENT_ID_1", date(2026, 5, 26))
        )

    async def test_async_cancel_meal_rejects_http_failure(self) -> None:
        session = _session_for_cancel(_JsonResponse({"Status": True}, status=500))
        client = _authenticated_client(session)

        with self.assertRaisesRegex(MealCancellationFailed, "http_error"):
            await client.async_cancel_meal("CLIENT_ID_1", date(2026, 5, 26))

        self.assertEqual(len(session.post_urls), 1)

    async def test_async_cancel_meal_rejects_false_or_missing_status(self) -> None:
        for response in (_JsonResponse({"Status": False}), _JsonResponse({"Ok": True})):
            with self.subTest(response=response.payload):
                session = _session_for_cancel(response)
                client = _authenticated_client(session)

                with self.assertRaisesRegex(MealCancellationFailed, "rejected"):
                    await client.async_cancel_meal("CLIENT_ID_1", date(2026, 5, 26))

                self.assertEqual(len(session.post_urls), 1)

    async def test_async_cancel_meal_rejects_non_json_response(self) -> None:
        session = _session_for_cancel(_JsonResponse(json_error=ValueError("not json")))
        client = _authenticated_client(session)

        with self.assertRaisesRegex(MealCancellationFailed, "invalid_response"):
            await client.async_cancel_meal("CLIENT_ID_1", date(2026, 5, 26))

        self.assertEqual(len(session.post_urls), 1)

    async def test_async_cancel_meal_requires_post_refresh_confirmation(self) -> None:
        session = _session_for_cancel(
            _JsonResponse({"Status": True}),
            post_order_html=_pre_cancel_order_html(),
        )
        client = _authenticated_client(session)

        with self.assertRaisesRegex(MealCancellationFailed, "confirmation_failed"):
            await client.async_cancel_meal("CLIENT_ID_1", date(2026, 5, 26))

        self.assertEqual(len(session.post_urls), 1)


class CancelMealServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_calls_coordinator_with_parsed_date(self) -> None:
        coordinator = _ServiceCoordinator()
        hass = SimpleNamespace(data={DOMAIN: {"entry-id": coordinator}})

        await _async_handle_cancel_meal_service(
            hass,
            ServiceCall(
                {
                    ATTR_CONFIG_ENTRY_ID: "entry-id",
                    ATTR_CHILD_ID: "CLIENT_ID_1",
                    ATTR_DATE: "2026-05-26",
                }
            ),
        )

        self.assertEqual(coordinator.calls, [("CLIENT_ID_1", date(2026, 5, 26))])

    async def test_service_rejects_missing_entry_and_bad_date(self) -> None:
        hass = SimpleNamespace(data={DOMAIN: {}})

        with self.assertRaisesRegex(HomeAssistantError, "entry not found"):
            await _async_handle_cancel_meal_service(
                hass,
                ServiceCall(
                    {
                        ATTR_CONFIG_ENTRY_ID: "missing",
                        ATTR_CHILD_ID: "CLIENT_ID_1",
                        ATTR_DATE: "2026-05-26",
                    }
                ),
            )

        with self.assertRaisesRegex(HomeAssistantError, "Invalid"):
            await _async_handle_cancel_meal_service(
                hass,
                ServiceCall(
                    {
                        ATTR_CONFIG_ENTRY_ID: "missing",
                        ATTR_CHILD_ID: "CLIENT_ID_1",
                        ATTR_DATE: "26.05.2026",
                    }
                ),
            )


def _pre_cancel_order_html() -> str:
    return Path("tests/fixtures/startedu_order_show_sanitized.html").read_text(
        encoding="utf-8"
    )


def _post_cancel_order_html() -> str:
    return (
        _pre_cancel_order_html()
        .replace(
            '<div class="day green" data-number="26">',
            '<div class="day cancelled" data-number="26">',
        )
        .replace(
            '<a class="button small red" data-action="cancel-meal" '
            'href="#">Odwołaj posiłek</a>',
            '<div class="cancellation-mark">Rezygnacja</div>',
        )
    )


def _account_data_from_order(order_html: str) -> StartEduAccountData:
    meals = parse_order_html(
        order_html,
        "CLIENT_ID_1",
        "CHILD_1",
        "paid",
        order_id="ORDER_ID",
    )
    return StartEduAccountData(
        fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
        children=(
            StartEduChild(
                child_id="CLIENT_ID_1",
                name="CHILD_1",
                meals=meals,
                unpaid_amount=Decimal("0"),
            ),
        ),
    )


def _session_for_cancel(
    post_response: _JsonResponse,
    *,
    post_order_html: str | None = None,
) -> _FakeSession:
    return _FakeSession(
        get_responses=[
            _TextResponse(DASHBOARD_HTML),
            _TextResponse("<html></html>"),
            _TextResponse(DASHBOARD_HTML),
            _TextResponse(_pre_cancel_order_html()),
            _TextResponse(REFUNDS_HTML),
            _TextResponse(COMMITMENTS_HTML),
            _TextResponse(DASHBOARD_HTML),
            _TextResponse("<html></html>"),
            _TextResponse(DASHBOARD_HTML),
            _TextResponse(post_order_html or _post_cancel_order_html()),
            _TextResponse(REFUNDS_HTML),
            _TextResponse(COMMITMENTS_HTML),
        ],
        post_responses=[post_response],
    )


def _authenticated_client(session: _FakeSession) -> StartEduClient:
    client = StartEduClient(
        session,
        "user",
        "password",
        base_url="https://s3.startedu.pl/Home/Client",
    )
    client._authenticated = True
    return client


class _FakeSession:
    def __init__(
        self,
        *,
        get_responses: list[_TextResponse],
        post_responses: list[_JsonResponse],
    ) -> None:
        self.get_responses = get_responses
        self.post_responses = post_responses
        self.get_urls: list[str] = []
        self.post_urls: list[str] = []
        self.post_kwargs: list[dict[str, object]] = []

    def get(self, url: str, **kwargs: object) -> _TextResponse:
        self.get_urls.append(url)
        return self.get_responses.pop(0)

    def post(self, url: str, **kwargs: object) -> _JsonResponse:
        self.post_urls.append(url)
        self.post_kwargs.append(dict(kwargs))
        return self.post_responses.pop(0)


class _TextResponse:
    def __init__(self, text: str, *, status: int = 200) -> None:
        self._text = text
        self.status = status

    async def __aenter__(self) -> _TextResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        return self._text


class _JsonResponse:
    def __init__(
        self,
        payload: dict[str, object] | None = None,
        *,
        status: int = 200,
        json_error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.status = status
        self.json_error = json_error

    async def __aenter__(self) -> _JsonResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self, **kwargs: object) -> dict[str, object] | None:
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class _ServiceCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, date]] = []

    async def async_cancel_meal(self, child_id: str, target_date: date) -> None:
        self.calls.append((child_id, target_date))
