# Development Setup

## Requirements

- Python 3.13 for CI parity.
- A Home Assistant development environment for full integration tests.
- A sanitized StartEdu test account for authentication discovery.

## Local Checks

```bash
python -m compileall custom_components tests
python -m pytest
```

## Home Assistant Manual Test

1. Add this repository as a HACS custom repository with category
   **Integration**, or copy `custom_components/startedu` into a Home Assistant
   development config.
2. Restart Home Assistant.
3. Add the StartEdu integration from the UI.
4. Confirm the calendar, sensors, refresh button, and `startedu.cancel_meal`
   service are available.

Never store real credentials, cookies, or captured authenticated pages in this
repository.
