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

## Test Account Usage

The shared StartEdu test account is read-only for this project. It may be used
to inspect account data, child switching, menus, payment status, and page
structure.

Do not use the test account to:

- Place meal orders.
- Cancel meals.
- Confirm cancellation dialogs or any other StartEdu modal that would mutate
  account state.

