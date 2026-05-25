from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from .models import StartEduAccountData, StartEduMeal

_LOGGER = logging.getLogger(__name__)

LOGIN_FIELD_HINTS = ("login", "email", "e-mail", "user", "student", "uczen")
PASSWORD_FIELD_HINTS = ("password", "haslo", "passwd")
MONEY_RE = r"([+-]?\d+(?:[ .]\d{3})*(?:[,.]\d{1,2})?)\s*(?:pln|zl|zloty)"
DATE_PATTERNS = (
    re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](20\d{2})\b"),
)


class StartEduError(Exception):
    """Base exception for StartEdu failures."""


class CannotConnect(StartEduError):
    """Raised when StartEdu cannot be reached or parsed."""


class InvalidAuth(StartEduError):
    """Raised when credentials are rejected by StartEdu."""


class StartEduDataError(StartEduError):
    """Raised when StartEdu returns an unexpected data shape."""


@dataclass(slots=True)
class LoginForm:
    action: str
    method: str
    fields: dict[str, str]
    login_field: str | None
    password_field: str | None


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

    async def async_login(self) -> None:
        """Authenticate against StartEdu and keep session cookies."""
        login_html = await self._request_text("get", self._base_url)
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
            raise InvalidAuth("StartEdu credentials were rejected")

        self._authenticated = True
        self._last_html = response_html

    async def async_get_account_data(self) -> StartEduAccountData:
        """Fetch and parse the current account snapshot."""
        if not self._authenticated:
            await self.async_login()

        html = self._last_html
        if html is None:
            html = await self._request_text("get", self._base_url)

        account_data = parse_account_html(html, datetime.now(timezone.utc))
        self._last_html = None
        return account_data

    async def _request_text(self, method: str, url: str, **kwargs: Any) -> str:
        request = getattr(self._session, method)
        try:
            async with request(url, **kwargs) as response:
                status = getattr(response, "status", 0)
                if status >= 400:
                    raise CannotConnect(f"StartEdu returned HTTP {status}")
                return await response.text()
        except StartEduError:
            raise
        except Exception as err:  # noqa: BLE001 - wrapped for HA config flow errors.
            raise CannotConnect("Could not communicate with StartEdu") from err


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
    balance = _extract_money_near_label(text, ("saldo", "balance"))
    refunds = _extract_money_near_label(text, ("zwroty", "refund", "refunds"))
    return StartEduAccountData(
        fetched_at=fetched_at,
        meals=meals,
        balance=balance,
        refunds=refunds,
    )


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
            part for part in parts if _extract_date(part) is None and not _is_money(part)
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
        return "cancelled"
    if any(marker in normalized for marker in ("ordered", "active", "zamow", "paid")):
        return "ordered"
    return None


def _is_status(text: str) -> bool:
    return _extract_status(text) is not None


def _is_money(text: str) -> bool:
    return re.fullmatch(rf"\s*{MONEY_RE}\s*", _strip_accents(text), re.IGNORECASE) is not None


def _contains_cancel_action(text: str) -> bool:
    normalized = _strip_accents(text).casefold()
    return "cancel" in normalized or "odwolaj" in normalized


def _extract_meal_id(text: str) -> str | None:
    match = re.search(r"\b(?:meal|posilek|order)[_-]?id[:=]\s*([A-Za-z0-9_-]+)", text)
    if match:
        return match.group(1)
    return None


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
