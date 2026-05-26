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

The shared StartEdu test account is read-only by default. It may be used to
inspect account data, child switching, menus, payment status, and page
structure without additional approval.

Do not use the test account to:

- Place meal orders.
- Confirm order editing dialogs or any other StartEdu modal that would mutate
  account state outside an approved test plan.

Mutating tests are allowed only when all of the following are true:

- A GitHub issue describes the exact action, target, and expected final state.
- The account owner explicitly approves the mutation before it is executed.
- The test is scoped to the smallest useful number of requests.
- Evidence is sanitized before being committed or posted to GitHub.
- Credentials, cookies, raw authenticated HTML, real client IDs, and real order
  IDs are never shared.

The 2026-05-26 controlled `CancelMeal` test for issue #7 is the only approved
mutation recorded so far.
