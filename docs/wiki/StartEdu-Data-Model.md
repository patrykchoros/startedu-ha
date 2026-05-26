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

Whole-day cancellation was validated once through the controlled issue #7 test:

```text
POST /Order/CancelMeal?orderId=<ORDER_ID>&dayNumber=<DAY>
```

The successful response shape was JSON with `Status: true`. A refreshed order
page then showed the day as `cancelled`, displayed `Rezygnacja`, and no longer
exposed `data-action="cancel-meal"`.

Other mutating endpoints, including `RevertMeal`, `CancelSingleDishType`,
`Resign`, and order editing endpoints, remain untested and must not be called
outside a separately approved test plan.
