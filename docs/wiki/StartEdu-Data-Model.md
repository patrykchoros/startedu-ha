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

