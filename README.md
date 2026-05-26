# StartEdu for Home Assistant

StartEdu is a custom Home Assistant integration for exposing meal and account data
from [startedu.pl](https://startedu.pl/) as Home Assistant entities.

This repository is currently in early MVP development. The first milestone is a
read-mostly HACS integration with a meal calendar, diagnostic sensors, and an
explicit user-triggered meal cancellation service.

## Read-Only Entities

- `calendar.<child>_meals` for upcoming ordered and cancelled meals.
- `sensor.<child>_next_meal` with structured meal attributes.
- Today/tomorrow menu and meal status sensors.
- Refund, unpaid amount, order status, and next-order-opening sensors when
  StartEdu exposes those values.
- Food and cancellation availability binary sensors.
- `button.<entry>_refresh_startedu_data` for manual user-triggered refresh.
- `startedu.cancel_meal` service for explicit whole-day cancellation.

## Installation

This integration is not released yet. During development, copy
`custom_components/startedu` into your Home Assistant `custom_components`
directory or add this repository as a HACS custom repository after releases are
available.

## Development Status

- HACS repository scaffold: in progress.
- StartEdu authentication and cancellation discovery: validated with a test
  account.
- Read-only entity model: implemented for calendar, sensors, binary sensors,
  and manual refresh.
- Meal cancellation action: implemented as an explicit service call.

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

The shared StartEdu test account is read-only by default. It may be used to
inspect account data, child switching, menus, payment status, and page
structure. Mutating tests require an explicit issue-backed plan and approval
before execution. Do not use the account to place meal orders or confirm any
StartEdu modal that would mutate account state outside an approved test plan.
