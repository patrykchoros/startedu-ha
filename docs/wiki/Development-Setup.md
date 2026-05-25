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

1. Copy `custom_components/startedu` into a Home Assistant development config.
2. Restart Home Assistant.
3. Add the StartEdu integration from the UI.
4. Confirm the calendar and sensors are created.

Never store real credentials, cookies, or captured authenticated pages in this
repository.

