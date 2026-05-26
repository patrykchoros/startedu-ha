from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit

from .entity_model import meal_type_from_label
from .models import (
    MEAL_STATUS_CANCELLED,
    MEAL_STATUS_NO_SCHOOL,
    MEAL_STATUS_NOT_ORDERED,
    MEAL_STATUS_PAID,
    MEAL_STATUS_UNKNOWN,
    MEAL_STATUS_UNPAID,
    StartEduAccountData,
    StartEduChild,
    StartEduMeal,
)

_LOGGER = logging.getLogger(__name__)

LOGIN_FIELD_HINTS = (
    "login",
    "email",
    "e-mail",
    "user",
    "student",
    "uczen",
    "identifier",
    "identyfikator",
)
PASSWORD_FIELD_HINTS = ("password", "haslo", "passwd")
MONEY_RE = r"([+-]?\d+(?:[ .]\d{3})*(?:[,.]\d{1,2})?)\s*(?:pln|zl|zloty)"
DATE_PATTERNS = (
    re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](20\d{2})\b"),
    re.compile(
        r"\b(\d{1,2})\s+"
        r"(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|"
        r"wrzesnia|października|pazdziernika|listopada|grudnia)\s+"
        r"(20\d{2})\b",
        re.IGNORECASE,
    ),
)
POLISH_MONTHS = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "wrzesnia": 9,
    "pazdziernika": 10,
    "października": 10,
    "listopada": 11,
    "grudnia": 12,
}


class StartEduError(Exception):
    """Base exception for StartEdu failures."""


class CannotConnect(StartEduError):
    """Raised when StartEdu cannot be reached or parsed."""


class InvalidAuth(StartEduError):
    """Raised when credentials are rejected by StartEdu."""


class StartEduDataError(StartEduError):
    """Raised when StartEdu returns an unexpected data shape."""


class MealCancellationError(StartEduError):
    """Raised when a StartEdu meal cancellation cannot be completed safely."""


class MealCancellationNotAllowed(MealCancellationError):
    """Raised when local preconditions refuse a cancellation request."""


class MealCancellationFailed(MealCancellationError):
    """Raised when StartEdu rejects or fails to confirm cancellation."""


@dataclass(slots=True)
class LoginForm:
    action: str
    method: str
    fields: dict[str, str]
    login_field: str | None
    password_field: str | None


@dataclass(frozen=True, slots=True)
class ResponseMetadata:
    status: int
    url: str


@dataclass(frozen=True, slots=True)
class DashboardChildLink:
    child_id: str
    name: str
    path: str
    is_active: bool = False


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    active_child_id: str
    active_child_name: str
    child_links: tuple[DashboardChildLink, ...]
    order_paths: tuple[str, ...]
    current_order_number: str | None = None
    current_month_order_status: str = MEAL_STATUS_UNKNOWN
    next_month_order_status: str = MEAL_STATUS_UNKNOWN
    next_month_ordering_available: bool | None = None
    next_order_opening_date: date | None = None


@dataclass(frozen=True, slots=True)
class MealCancellationTarget:
    order_id: str
    day_number: int


class StartEduClient:
    """Small async client for StartEdu.

    StartEdu does not currently publish an API for this integration. The client
    keeps all page-shape assumptions in one place so test-account discovery can
    refine it without touching Home Assistant entity code.
    """

    def __init__(
        self,
        session: Any,
        username: str,
        password: str,
        *,
        base_url: str = "https://startedu.pl/",
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        self._authenticated = False
        self._last_html: str | None = None
        self._last_response_metadata: ResponseMetadata | None = None

    async def async_login(self) -> None:
        """Authenticate against StartEdu and keep session cookies."""
        login_html = await self._request_text("get", self._base_url)
        login_page_metadata = self._last_response_metadata
        form = extract_login_form(login_html)
        payload = dict(form.fields)
        payload[form.login_field or "login"] = self._username
        payload[form.password_field or "password"] = self._password

        login_url = urljoin(self._base_url, form.action or self._base_url)
        method = "get" if form.method == "get" else "post"
        if method == "get":
            response_html = await self._request_text(method, login_url, params=payload)
        else:
            response_html = await self._request_text(method, login_url, data=payload)

        if looks_like_login_page(response_html):
            response_metadata = self._last_response_metadata
            _LOGGER.warning(
                "StartEdu login diagnostic: invalid_auth "
                "base_url=%s login_page_status=%s login_page_url=%s "
                "form_method=%s login_field=%s password_field=%s field_count=%d "
                "request_method=%s request_url=%s response_status=%s "
                "response_url=%s response_looks_like_login_page=%s",
                safe_url_for_log(self._base_url),
                _metadata_status(login_page_metadata),
                _metadata_url(login_page_metadata),
                method,
                form.login_field or "<fallback>",
                form.password_field or "<fallback>",
                len(form.fields),
                method,
                safe_url_for_log(login_url),
                _metadata_status(response_metadata),
                _metadata_url(response_metadata),
                True,
            )
            raise InvalidAuth("StartEdu credentials were rejected")

        self._authenticated = True
        self._last_html = response_html

    async def async_get_account_data(self) -> StartEduAccountData:
        """Fetch and parse the current account snapshot."""
        if not self._authenticated:
            await self.async_login()

        fetched_at = datetime.now(timezone.utc)
        html = self._last_html
        if html is None:
            html = await self._request_text("get", self._base_url)

        account_data = await self._async_parse_full_account_data(html, fetched_at)
        self._last_html = None
        return account_data

    async def async_cancel_meal(
        self,
        child_id: str,
        target_date: date,
    ) -> StartEduAccountData:
        """Cancel one whole-day meal after fresh validation and confirmation."""
        pre_action_data = await self.async_get_account_data()
        target = cancellation_target_from_data(
            pre_action_data,
            child_id,
            target_date,
        )

        response = await self._request_json(
            "post",
            self._cancel_meal_url(target.order_id, target.day_number),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        if response.get("Status") is not True:
            raise MealCancellationFailed("cancel_request_rejected")

        post_action_data = await self.async_get_account_data()
        if not cancellation_confirmed(post_action_data, child_id, target_date):
            raise MealCancellationFailed("cancel_confirmation_failed")
        return post_action_data

    async def _async_parse_full_account_data(
        self,
        dashboard_html: str,
        fetched_at: datetime,
    ) -> StartEduAccountData:
        first_dashboard = parse_dashboard_html(dashboard_html)
        children = []
        child_links = first_dashboard.child_links or (
            DashboardChildLink(
                child_id=first_dashboard.active_child_id,
                name=first_dashboard.active_child_name,
                path="",
                is_active=True,
            ),
        )

        for child_link in child_links:
            child_dashboard_html = dashboard_html
            if not child_link.is_active and child_link.path:
                child_dashboard_html = await self._request_text(
                    "get",
                    urljoin(self._base_url, child_link.path),
                )
            child_dashboard = parse_dashboard_html(child_dashboard_html)
            meals = []
            for order_path in child_dashboard.order_paths:
                order_id = _extract_order_id_from_path(order_path)
                order_html = await self._request_text(
                    "get",
                    urljoin(self._base_url, order_path),
                )
                meals.extend(
                    parse_order_html(
                        order_html,
                        child_dashboard.active_child_id,
                        child_dashboard.active_child_name,
                        child_dashboard.current_month_order_status,
                        order_id=order_id,
                    )
                )

            refunds = parse_refunds_html(
                await self._request_text("get", urljoin(self._base_url, "/Refunds"))
            )
            unpaid_amount = parse_commitments_html(
                await self._request_text("get", urljoin(self._base_url, "/Commitments"))
            )

            children.append(
                StartEduChild(
                    child_id=child_dashboard.active_child_id,
                    name=child_dashboard.active_child_name,
                    meals=tuple(meals),
                    current_month_order_status=(
                        child_dashboard.current_month_order_status
                    ),
                    next_month_order_status=child_dashboard.next_month_order_status,
                    next_month_ordering_available=(
                        child_dashboard.next_month_ordering_available
                    ),
                    next_order_opening_date=child_dashboard.next_order_opening_date,
                    current_order_number=child_dashboard.current_order_number,
                    refund_available=refunds,
                    unpaid_amount=unpaid_amount,
                )
            )

        return StartEduAccountData(
            fetched_at=fetched_at,
            children=tuple(children),
            active_child_id=first_dashboard.active_child_id,
            meals=tuple(meal for child in children for meal in child.meals),
            refunds=next(
                (
                    child.refund_available
                    for child in children
                    if child.refund_available
                ),
                None,
            ),
        )

    async def _request_text(self, method: str, url: str, **kwargs: Any) -> str:
        request = getattr(self._session, method)
        try:
            async with request(url, **kwargs) as response:
                status = getattr(response, "status", 0)
                response_url = getattr(response, "real_url", None)
                response_url = response_url or getattr(response, "url", url)
                self._last_response_metadata = ResponseMetadata(
                    status=status,
                    url=safe_url_for_log(str(response_url)),
                )
                if status >= 400:
                    _LOGGER.warning(
                        "StartEdu request diagnostic: http_error "
                        "method=%s request_url=%s status=%s response_url=%s",
                        method.upper(),
                        safe_url_for_log(url),
                        status,
                        self._last_response_metadata.url,
                    )
                    raise CannotConnect(f"StartEdu returned HTTP {status}")
                return await response.text()
        except StartEduError:
            raise
        except Exception as err:  # noqa: BLE001 - wrapped for HA config flow errors.
            _LOGGER.warning(
                "StartEdu request diagnostic: connection_error "
                "method=%s request_url=%s error_type=%s",
                method.upper(),
                safe_url_for_log(url),
                type(err).__name__,
            )
            raise CannotConnect("Could not communicate with StartEdu") from err

    async def _request_json(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        request = getattr(self._session, method)
        try:
            async with request(url, **kwargs) as response:
                status = getattr(response, "status", 0)
                if status >= 400:
                    raise MealCancellationFailed("cancel_request_http_error")
                try:
                    try:
                        payload = await response.json(content_type=None)
                    except TypeError:
                        payload = await response.json()
                except Exception as err:  # noqa: BLE001 - non-JSON StartEdu response.
                    raise MealCancellationFailed(
                        "cancel_request_invalid_response"
                    ) from err
                if not isinstance(payload, dict):
                    raise MealCancellationFailed("cancel_request_invalid_response")
                return payload
        except StartEduError:
            raise
        except Exception as err:  # noqa: BLE001
            raise CannotConnect("Could not communicate with StartEdu") from err

    def _cancel_meal_url(self, order_id: str, day_number: int) -> str:
        query = urlencode({"orderId": order_id, "dayNumber": day_number})
        return urljoin(self._base_url, f"/Order/CancelMeal?{query}")


def extract_login_form(html: str) -> LoginForm:
    parser = _LoginFormParser()
    parser.feed(html)
    if parser.login_form is not None:
        return parser.login_form
    return LoginForm(
        action="",
        method="post",
        fields={},
        login_field="login",
        password_field="password",
    )


def safe_url_for_log(url: str) -> str:
    """Return a URL safe for diagnostics by dropping query and credentials."""
    parsed = urlsplit(url)
    if not parsed.scheme and not parsed.netloc:
        return parsed.path or "<empty>"

    netloc = parsed.netloc.rsplit("@", 1)[-1]
    path = parsed.path or "/"
    return f"{parsed.scheme}://{netloc}{path}"


def _metadata_status(metadata: ResponseMetadata | None) -> int | str:
    return metadata.status if metadata is not None else "<unknown>"


def _metadata_url(metadata: ResponseMetadata | None) -> str:
    return metadata.url if metadata is not None else "<unknown>"


def looks_like_login_page(html: str) -> bool:
    lowered = _strip_accents(html).casefold()
    has_password_input = bool(
        re.search(r"<input[^>]+type=[\"']?password", lowered, re.IGNORECASE)
    )
    has_login_words = "logowanie" in lowered or "sign in" in lowered
    return has_password_input and has_login_words


def parse_account_html(
    html: str,
    fetched_at: datetime | None = None,
) -> StartEduAccountData:
    """Parse a sanitized StartEdu dashboard page into account data."""
    fetched_at = fetched_at or datetime.now(timezone.utc)
    text = html_to_text(html)
    rows = extract_table_rows(html)
    meals = tuple(sorted(_parse_meals(rows), key=lambda meal: (meal.date, meal.name)))
    dashboard = parse_dashboard_html(html)
    balance = _extract_money_near_label(text, ("saldo", "balance"))
    refunds = _extract_money_near_label(text, ("zwroty", "refund", "refunds"))
    child = StartEduChild(
        child_id=dashboard.active_child_id,
        name=dashboard.active_child_name,
        meals=meals,
        current_month_order_status=dashboard.current_month_order_status,
        next_month_order_status=dashboard.next_month_order_status,
        next_month_ordering_available=dashboard.next_month_ordering_available,
        next_order_opening_date=dashboard.next_order_opening_date,
        current_order_number=dashboard.current_order_number,
        refund_available=refunds,
        unpaid_amount=balance,
    )
    return StartEduAccountData(
        fetched_at=fetched_at,
        children=(child,) if meals else (),
        active_child_id=dashboard.active_child_id,
        meals=meals,
        balance=balance,
        refunds=refunds,
    )


def parse_dashboard_html(html: str) -> DashboardSnapshot:
    text = html_to_text(html)
    child_links = tuple(_extract_child_links(html))
    active_link = next((child for child in child_links if child.is_active), None)
    subaccount_match = re.search(r"Subkonto\s*\|\s*([^|]+)", text)
    active_child_name = (
        active_link.name
        if active_link is not None
        else (subaccount_match.group(1).strip() if subaccount_match else "StartEdu")
    )
    active_child_id = active_link.child_id if active_link is not None else "default"
    order_paths = tuple(
        dict.fromkeys(re.findall(r'href="(/Order/Show/[^"]+)"', html))
    )
    current_order = _extract_order_number(text)
    current_status = _extract_order_status(text)
    next_available = None
    next_status = MEAL_STATUS_UNKNOWN
    normalized_text = _strip_accents(text).casefold()
    if (
        "tworzenie zamowien" in normalized_text
        and "nie jest jeszcze mozliwe" in normalized_text
    ):
        next_available = False
        next_status = "not_available"
    elif "mozliwe" in normalized_text and "nadchodzacy miesiac" in normalized_text:
        next_available = True
        next_status = "available"
    opening_date = _extract_date(text)
    return DashboardSnapshot(
        active_child_id=active_child_id,
        active_child_name=active_child_name,
        child_links=child_links,
        order_paths=order_paths,
        current_order_number=current_order,
        current_month_order_status=current_status,
        next_month_order_status=next_status,
        next_month_ordering_available=next_available,
        next_order_opening_date=opening_date,
    )


def parse_order_html(
    html: str,
    child_id: str = "default",
    child_name: str = "StartEdu",
    default_status: str = MEAL_STATUS_UNKNOWN,
    *,
    order_id: str | None = None,
) -> tuple[StartEduMeal, ...]:
    order_number = _extract_order_number(html_to_text(html))
    year, month = _extract_order_year_month(html)
    if year is None or month is None:
        return ()

    meals: list[StartEduMeal] = []
    for day_match in re.finditer(
        r'<div class="day\s+([^"]*)"[^>]*data-number="(\d+)"[^>]*>'
        r'(.*?)(?=<div class="day\s|</div>\s*</div>\s*<script|<script)',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        classes, day_number, block = day_match.groups()
        day = date(year, month, int(day_number))
        day_text = html_to_text(block)
        price = _extract_money_near_label(day_text, ("cena",)) or _extract_first_money(
            day_text
        )
        can_cancel = _contains_cancel_meal_action(block)
        cancel_marker = "rezygnacja" in _strip_accents(day_text).casefold()
        day_status = _status_from_day_block(classes, day_text, default_status)
        raw = {
            "order_id": order_id,
            "day_number": int(day_number),
            "can_cancel_action": can_cancel,
            "cancel_marker": cancel_marker,
        }

        if day_status == MEAL_STATUS_NO_SCHOOL:
            meals.append(
                StartEduMeal(
                    meal_id=f"{order_number or 'order'}-{day_number}-no-school",
                    date=day,
                    name="No school meal",
                    menu=None,
                    meal_type="other",
                    child_id=child_id,
                    child_name=child_name,
                    status=MEAL_STATUS_NO_SCHOOL,
                    order_number=order_number,
                    price=price,
                    can_cancel=False,
                    raw=raw,
                )
            )
            continue

        slots = _extract_meal_slots(block)
        for label, menu in slots:
            meals.append(
                StartEduMeal(
                    meal_id=(
                        f"{order_number or 'order'}-"
                        f"{day_number}-{meal_type_from_label(label)}"
                    ),
                    date=day,
                    name=label,
                    menu=menu,
                    meal_type=meal_type_from_label(label),
                    child_id=child_id,
                    child_name=child_name,
                    status=day_status,
                    order_number=order_number,
                    price=price,
                    can_cancel=can_cancel,
                    raw=raw,
                )
            )
    return tuple(meals)


def cancellation_target_from_data(
    data: StartEduAccountData,
    child_id: str,
    target_date: date,
) -> MealCancellationTarget:
    child = next(
        (
            candidate
            for candidate in data.child_accounts
            if candidate.child_id == child_id
        ),
        None,
    )
    if child is None:
        raise MealCancellationNotAllowed("child_not_found")

    meals = tuple(meal for meal in child.meals if meal.date == target_date)
    if not meals:
        raise MealCancellationNotAllowed("day_missing")

    food_meals = tuple(meal for meal in meals if meal.status != MEAL_STATUS_NO_SCHOOL)
    if not food_meals:
        raise MealCancellationNotAllowed("day_unavailable")

    if any(meal.is_cancelled for meal in food_meals):
        raise MealCancellationNotAllowed("already_cancelled")

    if any(meal.status == MEAL_STATUS_NOT_ORDERED for meal in food_meals):
        raise MealCancellationNotAllowed("not_ordered")

    if not any(_meal_has_cancel_action(meal) for meal in food_meals):
        raise MealCancellationNotAllowed("missing_cancel_action")

    order_ids = {
        order_id
        for meal in food_meals
        if (order_id := _meal_order_id(meal)) is not None
    }
    if not order_ids:
        raise MealCancellationNotAllowed("order_missing")
    if len(order_ids) > 1:
        raise MealCancellationNotAllowed("ambiguous_order")

    day_numbers = {
        day_number
        for meal in food_meals
        if (day_number := _meal_day_number(meal)) is not None
    }
    if not day_numbers:
        raise MealCancellationNotAllowed("day_number_missing")
    if len(day_numbers) > 1:
        raise MealCancellationNotAllowed("ambiguous_day")

    return MealCancellationTarget(
        order_id=order_ids.pop(),
        day_number=day_numbers.pop(),
    )


def cancellation_confirmed(
    data: StartEduAccountData,
    child_id: str,
    target_date: date,
) -> bool:
    child = next(
        (
            candidate
            for candidate in data.child_accounts
            if candidate.child_id == child_id
        ),
        None,
    )
    if child is None:
        return False

    meals = tuple(
        meal
        for meal in child.meals
        if meal.date == target_date and meal.status != MEAL_STATUS_NO_SCHOOL
    )
    if not meals:
        return False

    return (
        all(meal.is_cancelled for meal in meals)
        and any(_meal_has_cancel_marker(meal) for meal in meals)
        and not any(_meal_has_cancel_action(meal) for meal in meals)
    )


def parse_refunds_html(html: str) -> Decimal | None:
    text = html_to_text(html)
    match = re.search(r"Aktualnie\s+" + MONEY_RE, _strip_accents(text), re.IGNORECASE)
    if match:
        return _parse_decimal(match.group(1))
    return _extract_money_near_label(text, ("zwroty", "refund"))


def parse_commitments_html(html: str) -> Decimal | None:
    text = html_to_text(html)
    rows = extract_table_rows(html)
    values = []
    for row in rows:
        normalized = _strip_accents(row).casefold()
        if "oplata za posilki" not in normalized:
            continue
        money_values = re.findall(MONEY_RE, normalized, re.IGNORECASE)
        if money_values:
            parsed_value = _parse_decimal(money_values[-1])
            if parsed_value is not None:
                values.append(parsed_value)
    if values:
        return sum(values, Decimal("0"))
    if "wszystkie zobowiazania sa uregulowane" in _strip_accents(text).casefold():
        return Decimal("0")
    return None


def html_to_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def extract_table_rows(html: str) -> list[str]:
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL)
    if rows:
        return [html_to_text(row) for row in rows]
    return [html_to_text(html)]


def _parse_meals(rows: list[str]) -> list[StartEduMeal]:
    meals: list[StartEduMeal] = []
    seen: set[tuple[date, str | None, str, str | None]] = set()
    for row in rows:
        meal_date = _extract_date(row)
        if meal_date is None:
            continue

        parts = [part.strip() for part in row.split("|") if part.strip()]
        parts_without_date = [
            part
            for part in parts
            if _extract_date(part) is None and not _is_money(part)
        ]
        status = _extract_status(row)
        child_name = parts_without_date[0] if len(parts_without_date) >= 2 else None
        name = _extract_meal_name(parts_without_date, status)
        price = _extract_first_money(row)
        can_cancel = _contains_cancel_action(row)
        meal_id = _extract_meal_id(row)

        key = (meal_date, child_name, name, status)
        if key in seen:
            continue
        seen.add(key)

        meals.append(
            StartEduMeal(
                meal_id=meal_id,
                date=meal_date,
                name=name,
                menu=None,
                meal_type=meal_type_from_label(name),
                child_name=child_name,
                status=status,
                price=price,
                can_cancel=can_cancel,
            )
        )
    return meals


def _extract_meal_name(parts: list[str], status: str | None) -> str:
    candidates = [part for part in parts if part != status and not _is_status(part)]
    if len(candidates) >= 2:
        return candidates[1]
    if candidates:
        return candidates[0]
    return "Meal"


def _extract_date(text: str) -> date | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        if pattern.pattern.startswith("\\b(20"):
            year, month, day = (int(group) for group in match.groups())
        elif "stycznia" in pattern.pattern:
            day = int(match.group(1))
            month = POLISH_MONTHS[_strip_accents(match.group(2)).casefold()]
            year = int(match.group(3))
        else:
            day, month, year = (int(group) for group in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _extract_money_near_label(text: str, labels: tuple[str, ...]) -> Decimal | None:
    normalized = _strip_accents(text).casefold()
    for label in labels:
        match = re.search(rf"{re.escape(label)}[^0-9+-]{{0,40}}{MONEY_RE}", normalized)
        if match:
            return _parse_decimal(match.group(1))
    return None


def _extract_first_money(text: str) -> Decimal | None:
    match = re.search(MONEY_RE, _strip_accents(text), re.IGNORECASE)
    if match is None:
        return None
    return _parse_decimal(match.group(1))


def _parse_decimal(value: str) -> Decimal | None:
    compact = value.replace(" ", "")
    if "," in compact:
        normalized = compact.replace(".", "").replace(",", ".")
    else:
        normalized = compact
    try:
        return Decimal(normalized)
    except InvalidOperation:
        _LOGGER.debug("Could not parse StartEdu money value: %s", value)
        return None


def _extract_status(text: str) -> str | None:
    normalized = _strip_accents(text).casefold()
    if any(marker in normalized for marker in ("cancelled", "canceled", "odwol")):
        return MEAL_STATUS_CANCELLED
    if any(marker in normalized for marker in ("nieoplac", "unpaid")):
        return MEAL_STATUS_UNPAID
    if any(
        marker in normalized
        for marker in ("ordered", "active", "zamow", "paid", "oplac")
    ):
        return MEAL_STATUS_PAID
    return None


def _is_status(text: str) -> bool:
    return _extract_status(text) is not None


def _is_money(text: str) -> bool:
    return (
        re.fullmatch(rf"\s*{MONEY_RE}\s*", _strip_accents(text), re.IGNORECASE)
        is not None
    )


def _contains_cancel_action(text: str) -> bool:
    normalized = _strip_accents(text).casefold()
    return "cancel" in normalized or "odwolaj" in normalized


def _contains_cancel_meal_action(html: str) -> bool:
    return bool(
        re.search(
            r"data-action\s*=\s*[\"']cancel-meal[\"']",
            html,
            flags=re.IGNORECASE,
        )
    )


def _extract_order_id_from_path(path: str) -> str | None:
    match = re.search(r"/Order/Show/([^/?#]+)", path, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _meal_order_id(meal: StartEduMeal) -> str | None:
    value = meal.raw.get("order_id")
    return str(value) if value else None


def _meal_day_number(meal: StartEduMeal) -> int | None:
    value = meal.raw.get("day_number")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _meal_has_cancel_action(meal: StartEduMeal) -> bool:
    return bool(meal.raw.get("can_cancel_action", meal.can_cancel))


def _meal_has_cancel_marker(meal: StartEduMeal) -> bool:
    return bool(meal.raw.get("cancel_marker"))


def _extract_meal_id(text: str) -> str | None:
    match = re.search(r"\b(?:meal|posilek|order)[_-]?id[:=]\s*([A-Za-z0-9_-]+)", text)
    if match:
        return match.group(1)
    return None


def _extract_child_links(html: str) -> list[DashboardChildLink]:
    links = []
    for match in re.finditer(
        r'<a\s+class="([^"]*)" href="(/User/SwitchClient/([^"]+))">([^<]+)</a>',
        html,
        flags=re.IGNORECASE,
    ):
        class_name, path, child_id, child_name = match.groups()
        links.append(
            DashboardChildLink(
                child_id=child_id,
                name=html_to_text(child_name),
                path=path,
                is_active="current" in class_name.split(),
            )
        )
    return links


def _extract_order_number(text: str) -> str | None:
    match = re.search(r"SE/[A-Za-z0-9_-]+/\d{1,2}/20\d{2}", text)
    return match.group(0) if match else None


def _extract_order_year_month(html: str) -> tuple[int | None, int | None]:
    text = html_to_text(html)
    match = re.search(r"SE/[A-Za-z0-9_-]+/(\d{1,2})/(20\d{2})", text)
    if match:
        return int(match.group(2)), int(match.group(1))
    return None, None


def _extract_order_status(text: str) -> str:
    normalized = _strip_accents(text).casefold()
    if "zostalo oplacone" in normalized or "oplacone" in normalized:
        return MEAL_STATUS_PAID
    if "nieoplacone" in normalized or "do zaplaty" in normalized:
        return MEAL_STATUS_UNPAID
    return MEAL_STATUS_UNKNOWN


def _status_from_day_block(classes: str, text: str, default_status: str) -> str:
    normalized = _strip_accents(f"{classes} {text}").casefold()
    if "cancelled" in normalized or "rezygnacja" in normalized:
        return MEAL_STATUS_CANCELLED
    if "disabled" in normalized or "dzien niedostepny" in normalized:
        return MEAL_STATUS_NO_SCHOOL
    if default_status in {MEAL_STATUS_PAID, MEAL_STATUS_UNPAID}:
        return default_status
    return MEAL_STATUS_UNKNOWN


def _extract_meal_slots(block: str) -> list[tuple[str, str]]:
    slots = []
    matches = list(
        re.finditer(
            r"<h[1-6][^>]*>(.*?)</h[1-6]>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    for index, match in enumerate(matches):
        label = html_to_text(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        fragment = block[start:end]
        fragment = re.sub(r"Cena:\s*" + MONEY_RE, "", fragment, flags=re.IGNORECASE)
        fragment = re.sub(
            r"<a\b[^>]*>.*?</a>",
            "",
            fragment,
            flags=re.IGNORECASE | re.DOTALL,
        )
        menu = html_to_text(fragment)
        if label and menu:
            slots.append((label, menu))
    return slots


def _strip_accents(value: str) -> str:
    translation = str.maketrans(
        {
            "ą": "a",
            "ć": "c",
            "ę": "e",
            "ł": "l",
            "ń": "n",
            "ó": "o",
            "ś": "s",
            "ż": "z",
            "ź": "z",
            "Ą": "A",
            "Ć": "C",
            "Ę": "E",
            "Ł": "L",
            "Ń": "N",
            "Ó": "O",
            "Ś": "S",
            "Ż": "Z",
            "Ź": "Z",
        }
    )
    return value.translate(translation)


class _LoginFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_form = False
        self._current_action = ""
        self._current_method = "post"
        self._current_fields: dict[str, str] = {}
        self._current_login_field: str | None = None
        self._current_password_field: str | None = None
        self.login_form: LoginForm | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name.casefold(): value or "" for name, value in attrs}
        if tag.casefold() == "form" and self.login_form is None:
            self._in_form = True
            self._current_action = attrs_dict.get("action", "")
            self._current_method = attrs_dict.get("method", "post").casefold()
            self._current_fields = {}
            self._current_login_field = None
            self._current_password_field = None
            return

        if not self._in_form or tag.casefold() != "input":
            return

        name = attrs_dict.get("name")
        if not name:
            return

        input_type = attrs_dict.get("type", "text").casefold()
        hint = " ".join(
            (
                name,
                attrs_dict.get("id", ""),
                attrs_dict.get("placeholder", ""),
                attrs_dict.get("autocomplete", ""),
            )
        )
        normalized_hint = _strip_accents(hint).casefold()
        self._current_fields[name] = attrs_dict.get("value", "")

        if input_type == "password" or any(
            marker in normalized_hint for marker in PASSWORD_FIELD_HINTS
        ):
            self._current_password_field = name
        elif input_type in {"email", "text", "tel"} and any(
            marker in normalized_hint for marker in LOGIN_FIELD_HINTS
        ):
            self._current_login_field = name

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "form" or not self._in_form:
            return

        if self._current_password_field is not None:
            self.login_form = LoginForm(
                action=self._current_action,
                method=self._current_method,
                fields=self._current_fields,
                login_field=self._current_login_field,
                password_field=self._current_password_field,
            )
        self._in_form = False


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"td", "th", "tr", "li", "br"}:
            self.parts.append("|")

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)
