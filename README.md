# StartEdu for Home Assistant

StartEdu is a custom Home Assistant integration for exposing meal and account data
from [startedu.pl](https://startedu.pl/) as Home Assistant entities.

This repository is currently in early MVP development. The first milestone is a
read-mostly HACS integration with a meal calendar, diagnostic sensors, and an
explicit user-triggered meal cancellation service.

## Features

- `calendar.<child>_meals` for upcoming ordered and cancelled meals.
- `sensor.<child>_next_meal` with structured meal attributes.
- Today/tomorrow menu and meal status sensors.
- Refund, unpaid amount, order status, and next-order-opening sensors when
  StartEdu exposes those values.
- Food and cancellation availability binary sensors.
- `button.<entry>_refresh_startedu_data` for manual user-triggered refresh.
- `startedu.cancel_meal` service for explicit whole-day cancellation.

## Installation

This integration is prepared for installation as a HACS custom repository. It is
not published as a default HACS repository yet.

### HACS Custom Repository

1. In Home Assistant, open HACS.
2. Open **Custom repositories**.
3. Add this repository URL:

   ```text
   https://github.com/patrykchoros/startedu-ha
   ```

4. Select **Integration** as the category.
5. Download **StartEdu** from HACS.
6. Restart Home Assistant.
7. Go to **Settings > Devices & services > Add integration** and add
   **StartEdu**.
8. Enter StartEdu credentials and adjust options if needed.

### Manual Development Install

1. Copy `custom_components/startedu` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.
3. Add **StartEdu** from **Settings > Devices & services > Add integration**.

## Development Status

- HACS custom repository metadata: ready for custom repository installation.
- Default HACS repository publication: not requested yet.
- StartEdu authentication and cancellation discovery: validated with a test
  account.
- Read-only entity model: implemented for calendar, sensors, binary sensors,
  and manual refresh.
- Meal cancellation action: implemented as an explicit service call.

Before public distribution, follow the
[release checklist](docs/release-checklist.md).

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
