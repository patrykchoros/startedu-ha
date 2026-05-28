# StartEdu for Home Assistant

StartEdu is a custom Home Assistant integration for exposing meal and account data
from [startedu.pl](https://startedu.pl/) as Home Assistant entities.

This repository is currently in early MVP development. The first milestone is a
read-mostly HACS integration with a meal calendar, diagnostic sensors, and an
explicit user-triggered meal cancellation service.

## Features

- `calendar.<child>_meals` for upcoming ordered and cancelled meals.
- Today/tomorrow menu and meal status sensors.
- Refund, unpaid amount, order status, and next-order-opening sensors when
  StartEdu exposes those values.
- Main-device synchronization status sensors for the current refresh activity,
  last refresh result, and last refresh timestamp.
- Food and cancellation availability binary sensors.
- `button.<entry>_refresh_startedu_data` for manual user-triggered refresh.
- Child-device buttons for cancelling today's or tomorrow's whole-day meals.
- `startedu.cancel_meal` service for explicit whole-day cancellation.

## User Guide

After the integration is installed, see the [StartEdu user guide](docs/user-guide.md)
for entity meanings, refresh behavior, cancellation safety, dashboard examples,
and automation examples.

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
- Meal cancellation action: implemented as child-device buttons and an explicit
  service call.

Before public distribution or broader Home Assistant testing, follow the
[release process](docs/release-process.md), the
[release checklist](docs/release-checklist.md), and the
[release notes template](docs/release-notes-template.md). The recommended
install target for testers should be a GitHub Release tag rather than an
unlabeled `main` commit, except during short-lived issue diagnostics.

## Security

Credentials are stored in Home Assistant's config entry storage. Do not commit
real StartEdu credentials, cookies, captured authenticated HTML, or network traces
to this repository.

For local test-account discovery, credentials may be stored outside Git in an
ignored file such as `.local/startedu-test.env`:

```dotenv
STARTEDU_USERNAME=
STARTEDU_PASSWORD=
```

Keep that file local only. Do not paste its contents into issues, wiki pages,
fixtures, screenshots, or logs.

The shared StartEdu test account is read-only by default. It may be used to
inspect account data, child switching, menus, payment status, and page
structure. Mutating tests require an explicit issue-backed plan and approval
before execution. Do not use the account to place meal orders or confirm any
StartEdu modal that would mutate account state outside an approved test plan.

For faster parser/authentication diagnostics without installing the integration
in Home Assistant, run the local sanitized probe:

```bash
python scripts/startedu_probe.py
```

To verify the Home Assistant entity model that would be produced from the same
StartEdu pages, run:

```bash
python scripts/startedu_probe.py --entities
```

The probe uses the same StartEdu client as the integration and avoids printing
credentials, child identifiers, order identifiers, cookies, or raw HTML.
