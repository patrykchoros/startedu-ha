# StartEdu Data Model

The integration stores a normalized account snapshot in memory:

- `fetched_at`: timestamp for the last successful StartEdu fetch.
- `meals`: ordered list of meal entries.
- `balance`: optional account balance when StartEdu exposes it.
- `refunds`: optional refund value when StartEdu exposes it.

Each meal may include:

- StartEdu meal identifier, if visible.
- Date.
- Meal name.
- Child or student name.
- Status.
- Price.
- Whether the page exposes a cancellation affordance.

Authenticated HTML, raw cookies, and personal data must be sanitized before they
are added to fixtures or issues.

## Observed Read-Only Sources

The current discovery notes are stored in `docs/startedu-flow-discovery.md`.
The main read-only sources are:

- `/Home/Client` for active child, child switching, current and next month state,
  and links to order details.
- `/Order/Show/<ORDER_ID>` for the monthly menu and day-level status.
- `/Refunds` for refund amount and refund transaction history.
- `/Commitments` for payment obligations and order payment status.

Mutating order/cancellation endpoints were identified in JavaScript but must not
be called during read-only discovery.
