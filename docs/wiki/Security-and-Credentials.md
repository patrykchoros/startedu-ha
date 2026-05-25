# Security and Credentials

StartEdu credentials are collected through the Home Assistant UI config flow and
stored in Home Assistant config entry storage.

Project rules:

- Do not commit real credentials.
- Do not commit authenticated HTML without sanitization.
- Do not paste cookies, tokens, account identifiers, or student data into
  GitHub issues.
- Redact credentials from diagnostics.
- Use a test account for endpoint discovery.

