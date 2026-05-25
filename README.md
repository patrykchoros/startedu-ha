# StartEdu for Home Assistant

StartEdu is a custom Home Assistant integration for exposing meal and account data
from [startedu.pl](https://startedu.pl/) as Home Assistant entities.

This repository is currently in early MVP development. The first milestone is a
read-only HACS integration with a meal calendar and diagnostic sensors. Meal
cancellation will be added only after the StartEdu flow and cancellation rules are
confirmed with a test account.

## Planned Entities

- `calendar.startedu_meals` for upcoming ordered and cancelled meals.
- A nearest-meal sensor with structured meal attributes.
- Account balance and refund sensors when StartEdu exposes those values.
- Sync status and last successful update diagnostic sensors.

## Installation

This integration is not released yet. During development, copy
`custom_components/startedu` into your Home Assistant `custom_components`
directory or add this repository as a HACS custom repository after releases are
available.

## Development Status

- HACS repository scaffold: in progress.
- StartEdu authentication discovery: pending test account validation.
- Read-only entity model: in progress.
- Meal cancellation action: planned, not implemented.

## Security

Credentials are stored in Home Assistant's config entry storage. Do not commit
real StartEdu credentials, cookies, captured authenticated HTML, or network traces
to this repository.

For local test-account discovery, credentials may be stored outside Git in an
ignored file such as `.local/startedu-test.env`:

```dotenv
STARTEDU_USERNAME=
STARTEDU_PASSWORD=
STARTEDU_BASE_URL=https://s3.startedu.pl/Home/Client
```

Keep that file local only. Do not paste its contents into issues, wiki pages,
fixtures, screenshots, or logs.

The shared StartEdu test account is read-only for this project. It may be used
to inspect account data, child switching, menus, payment status, and page
structure. Do not use it to place meal orders, cancel meals, or confirm any
StartEdu modal that would mutate account state.
