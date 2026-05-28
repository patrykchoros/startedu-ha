# Development Setup

## Requirements

- Python 3.13 for CI parity.
- A Home Assistant development environment for full integration tests.
- A sanitized StartEdu test account for authentication discovery.

## Local Checks

```bash
python -m compileall custom_components tests
python -m unittest discover -s tests
```

## Local StartEdu Probe

Use the local probe to test StartEdu authentication and parsing without
installing or restarting Home Assistant:

```bash
python scripts/startedu_probe.py
```

The probe uses the same `StartEduClient` parser as the integration, but runs
with a tiny local HTTP session and prints only sanitized summary data:

- child count and per-child meal counts,
- meal date range,
- today/tomorrow status flags,
- refund and unpaid totals,
- redacted StartEdu diagnostics from the client logger.

For repeat local runs, credentials may be placed outside Git in
`.local/startedu-test.env`:

```dotenv
STARTEDU_USERNAME=
STARTEDU_PASSWORD=
```

JSON output is available for attaching sanitized diagnostics to issues:

```bash
python scripts/startedu_probe.py --json
```

Do not paste credentials, cookies, raw HTML, child names, child identifiers, or
order identifiers into issues. The probe output is designed to avoid those
values by default.

## Home Assistant Manual Test

1. Add this repository as a HACS custom repository with category
   **Integration**, or copy `custom_components/startedu` into a Home Assistant
   development config.
2. Restart Home Assistant.
3. Add the StartEdu integration from the UI.
4. Confirm the calendar, sensors, refresh button, child cancellation buttons,
   and `startedu.cancel_meal` service are available.

Never store real credentials, cookies, or captured authenticated pages in this
repository.

## Release Workflow

Before asking users to install or test a specific version, follow the
[Release Process](Release-Process), [Release Checklist](Release-Checklist), and
[Release Notes Template](Release-Notes-Template).

Normal Home Assistant testing should use a GitHub Release tag. Raw `main` commit
SHAs are reserved for short-lived diagnostics in an active issue.
