#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from getpass import getpass
from http.cookiejar import CookieJar
import json
import logging
import os
from pathlib import Path
import sys
import types
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.error import HTTPError
from urllib.request import (
    HTTPCookieProcessor,
    Request,
    build_opener,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _install_local_package_stubs() -> None:
    custom_components = sys.modules.get("custom_components")
    if custom_components is None:
        custom_components = types.ModuleType("custom_components")
        sys.modules["custom_components"] = custom_components
    custom_components.__path__ = [str(ROOT / "custom_components")]

    startedu = sys.modules.get("custom_components.startedu")
    if startedu is None:
        startedu = types.ModuleType("custom_components.startedu")
        sys.modules["custom_components.startedu"] = startedu
    startedu.__path__ = [str(ROOT / "custom_components" / "startedu")]


_install_local_package_stubs()

from custom_components.startedu.client import StartEduClient, StartEduError
from custom_components.startedu.const import DEFAULT_BASE_URL
from custom_components.startedu.entity_model import (
    can_cancel,
    day_meals,
    day_status,
    has_food,
    next_child_meal,
)
from custom_components.startedu.models import StartEduAccountData, StartEduChild

DEFAULT_ENV_FILE = ".local/startedu-test.env"


@dataclass(frozen=True, slots=True)
class ProbeOptions:
    username: str
    password: str
    base_url: str
    timeout: float


class UrllibSession:
    """Tiny aiohttp-like session for local StartEdu probes."""

    def __init__(self, timeout: float) -> None:
        self._timeout = timeout
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def get(self, url: str, **kwargs: object) -> "UrllibRequestContext":
        return UrllibRequestContext(self._opener, "GET", url, self._timeout, kwargs)

    def post(self, url: str, **kwargs: object) -> "UrllibRequestContext":
        return UrllibRequestContext(self._opener, "POST", url, self._timeout, kwargs)


class UrllibRequestContext:
    def __init__(
        self,
        opener: Any,
        method: str,
        url: str,
        timeout: float,
        kwargs: Mapping[str, object],
    ) -> None:
        self._opener = opener
        self._method = method
        self._url = url
        self._timeout = timeout
        self._kwargs = dict(kwargs)
        self._response: UrllibResponse | None = None

    async def __aenter__(self) -> "UrllibResponse":
        self._response = await asyncio.to_thread(self._open)
        return self._response

    async def __aexit__(self, *args: object) -> None:
        return None

    def _open(self) -> "UrllibResponse":
        url = _url_with_params(self._url, self._kwargs.pop("params", None))
        headers = dict(self._kwargs.pop("headers", {}) or {})
        raw_data = self._kwargs.pop("data", None)
        data = _encode_post_data(raw_data)
        if isinstance(raw_data, Mapping):
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request = Request(url, data=data, headers=headers, method=self._method)
        try:
            response = self._opener.open(request, timeout=self._timeout)
        except HTTPError as err:
            return _response_from_urllib(err)
        return _response_from_urllib(response)


def _response_from_urllib(response: Any) -> "UrllibResponse":
    try:
        status = int(getattr(response, "status", response.getcode()))
        final_url = response.geturl()
        response_headers = response.headers
        body = response.read()
        return UrllibResponse(status, final_url, response_headers, body)
    finally:
        response.close()


class UrllibResponse:
    def __init__(self, status: int, url: str, headers: Any, body: bytes) -> None:
        self.status = status
        self.url = url
        self.real_url = url
        self._headers = headers
        self._body = body

    async def text(self) -> str:
        charset = self._headers.get_content_charset() or "utf-8"
        return self._body.decode(charset, errors="replace")

    async def json(self, **_: object) -> object:
        return json.loads(await self.text())


def _url_with_params(url: str, params: object) -> str:
    if not params:
        return url
    if isinstance(params, Mapping):
        encoded = urlencode(params)
    else:
        encoded = str(params)
    scheme, netloc, path, query, fragment = urlsplit(url)
    query = f"{query}&{encoded}" if query else encoded
    return urlunsplit((scheme, netloc, path, query, fragment))


def _encode_post_data(data: object) -> bytes | None:
    if data is None:
        return None
    if isinstance(data, bytes):
        return data
    if isinstance(data, Mapping):
        return urlencode(data).encode()
    return str(data).encode()


async def fetch_account_data(options: ProbeOptions) -> StartEduAccountData:
    session = UrllibSession(timeout=options.timeout)
    client = StartEduClient(
        session,
        options.username,
        options.password,
        base_url=options.base_url,
    )
    return await client.async_get_account_data()


def build_probe_report(
    data: StartEduAccountData,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    children = list(data.child_accounts)
    return {
        "fetched_at": data.fetched_at.isoformat(),
        "today": today.isoformat(),
        "children_count": len(children),
        "total_meals": sum(len(child.meals) for child in children),
        "meal_date_range": _meal_date_range(children),
        "child_meal_counts": [len(child.meals) for child in children],
        "refunds": _decimal_to_string(data.refunds),
        "children": [
            _child_report(child, index, today)
            for index, child in enumerate(children, start=1)
        ],
        "warnings": _report_warnings(children, today),
    }


def _child_report(
    child: StartEduChild,
    index: int,
    today: date,
) -> dict[str, Any]:
    next_meal = next_child_meal(child, today)
    return {
        "index": index,
        "meal_count": len(child.meals),
        "meal_date_range": _meal_date_range([child]),
        "today": _day_report(child, today),
        "tomorrow": _day_report(child, today + timedelta(days=1)),
        "next_meal": (
            {
                "date": next_meal.date.isoformat(),
                "meal_type": next_meal.meal_type,
                "status": next_meal.status,
                "can_cancel": next_meal.can_cancel,
            }
            if next_meal is not None
            else None
        ),
        "current_month_order_status": child.current_month_order_status,
        "next_month_order_status": child.next_month_order_status,
        "next_month_ordering_available": child.next_month_ordering_available,
        "next_order_opening_date": (
            child.next_order_opening_date.isoformat()
            if child.next_order_opening_date is not None
            else None
        ),
        "refund_available": _decimal_to_string(child.refund_available),
        "unpaid_amount": _decimal_to_string(child.unpaid_amount),
    }


def _day_report(child: StartEduChild, target_date: date) -> dict[str, Any]:
    meals = day_meals(child, target_date)
    return {
        "date": target_date.isoformat(),
        "meal_count": len(meals),
        "status": day_status(child, target_date),
        "has_food": has_food(child, target_date),
        "can_cancel": can_cancel(child, target_date),
        "meal_types": sorted({meal.meal_type for meal in meals}),
    }


def _report_warnings(children: list[StartEduChild], today: date) -> list[str]:
    warnings = []
    if not children:
        warnings.append("no_children")
        return warnings

    total_meals = sum(len(child.meals) for child in children)
    if total_meals == 0:
        warnings.append("no_meals")
    if any(not child.meals for child in children):
        warnings.append("child_without_meals")
    latest_meal_date = max(
        (meal.date for child in children for meal in child.meals),
        default=None,
    )
    if latest_meal_date is not None and latest_meal_date < today:
        warnings.append("only_past_meals")
    if all(day_status(child, today) == "unknown" for child in children):
        warnings.append("today_unknown_for_all_children")
    return warnings


def _meal_date_range(children: list[StartEduChild]) -> str | None:
    dates = sorted(meal.date for child in children for meal in child.meals)
    if not dates:
        return None
    return f"{dates[0].isoformat()}..{dates[-1].isoformat()}"


def _decimal_to_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def format_probe_report(report: dict[str, Any]) -> str:
    lines = [
        "StartEdu probe result",
        f"fetched_at: {report['fetched_at']}",
        f"today: {report['today']}",
        (
            f"children: {report['children_count']} | "
            f"total_meals: {report['total_meals']} | "
            f"meal_date_range: {report['meal_date_range'] or '<empty>'}"
        ),
        f"child_meal_counts: {_format_counts(report['child_meal_counts'])}",
    ]
    if report["refunds"] is not None:
        lines.append(f"refunds: {report['refunds']} PLN")
    if report["warnings"]:
        lines.append(f"warnings: {', '.join(report['warnings'])}")

    for child in report["children"]:
        lines.extend(
            [
                "",
                (
                    f"child #{child['index']}: meals={child['meal_count']} "
                    f"dates={child['meal_date_range'] or '<empty>'} "
                    f"refund={child['refund_available'] or '<none>'} "
                    f"unpaid={child['unpaid_amount'] or '<none>'}"
                ),
                _format_day("today", child["today"]),
                _format_day("tomorrow", child["tomorrow"]),
                f"next_meal: {_format_next_meal(child['next_meal'])}",
                (
                    "order_status: "
                    f"current={child['current_month_order_status']} "
                    f"next={child['next_month_order_status']} "
                    f"next_available={child['next_month_ordering_available']}"
                ),
            ]
        )
    return "\n".join(lines)


def _format_counts(counts: list[int]) -> str:
    return ",".join(str(count) for count in counts) or "<empty>"


def _format_day(label: str, day: dict[str, Any]) -> str:
    meal_types = ",".join(day["meal_types"]) or "<none>"
    return (
        f"{label}: {day['date']} status={day['status']} "
        f"meals={day['meal_count']} has_food={day['has_food']} "
        f"can_cancel={day['can_cancel']} meal_types={meal_types}"
    )


def _format_next_meal(next_meal: dict[str, Any] | None) -> str:
    if next_meal is None:
        return "<none>"
    return (
        f"{next_meal['date']} {next_meal['meal_type']} "
        f"status={next_meal['status']} can_cancel={next_meal['can_cancel']}"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    env_parser = argparse.ArgumentParser(add_help=False)
    env_parser.add_argument(
        "--env-file",
        default=os.environ.get("STARTEDU_ENV_FILE", DEFAULT_ENV_FILE),
    )
    env_args, _ = env_parser.parse_known_args(argv)
    load_env_file(Path(env_args.env_file))

    parser = argparse.ArgumentParser(
        description="Run a sanitized StartEdu client probe without Home Assistant.",
        parents=[env_parser],
    )
    parser.add_argument("--username", default=os.environ.get("STARTEDU_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("STARTEDU_PASSWORD"))
    parser.add_argument(
        "--base-url",
        default=os.environ.get("STARTEDU_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json", action="store_true", help="print JSON output")
    parser.add_argument(
        "--fail-on-empty-meals",
        action="store_true",
        help="exit non-zero when StartEdu returns no meal entries",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("STARTEDU_LOG_LEVEL", "WARNING"),
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser.parse_args(argv)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def options_from_args(args: argparse.Namespace) -> ProbeOptions:
    username = args.username or input("StartEdu username: ")
    password = args.password or getpass("StartEdu password: ")
    return ProbeOptions(
        username=username,
        password=password,
        base_url=args.base_url,
        timeout=args.timeout,
    )


async def async_main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s:%(name)s:%(message)s",
    )
    try:
        data = await fetch_account_data(options_from_args(args))
    except StartEduError as err:
        print(f"StartEdu probe failed: {err}", file=sys.stderr)
        return 2

    report = build_probe_report(data)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    else:
        print(format_probe_report(report))

    if args.fail_on_empty_meals and report["total_meals"] == 0:
        return 3
    return 0


def _json_default(value: object) -> object:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if dataclass_is_instance(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dataclass_is_instance(value: object) -> bool:
    return hasattr(value, "__dataclass_fields__") and not isinstance(value, type)


def main() -> int:
    return asyncio.run(async_main(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
