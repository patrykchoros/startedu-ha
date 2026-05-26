# StartEdu Login and Data-Fetch Flow

Discovery date: 2026-05-25.
Controlled cancellation test date: 2026-05-26.

This document records the authenticated read-only flow observed with the shared
test account, plus one explicitly approved cancellation test. The account is
read-only by default. Do not place orders, cancel meals, revert cancellations,
or confirm any modal that mutates StartEdu state unless a separate issue-backed
test plan has been approved for that exact action.

## Login Flow

The project entry URL is:

```text
https://s3.startedu.pl/Home/Client
```

When no authenticated session exists, StartEdu redirects through:

```text
https://s3.startedu.pl/Home/Client
https://startedu.pl/Home/Client
https://startedu.pl?redirect=%2fHome%2fClient
```

The login page contains a classic HTML form:

```html
<form action="/User/SignIn" method="post" id="sign-in-form">
  <input id="Identifier" name="Identifier" type="text">
  <input id="Password" name="Password" type="password">
</form>
```

Client-side JavaScript rewrites the form action to a random sharded host
`s1.startedu.pl` through `s6.startedu.pl`, appends the original redirect query,
and posts to:

```text
POST https://sN.startedu.pl/User/SignIn?redirect=%2fHome%2fClient
```

The successful response observed during discovery returned `302 Found`, set the
session cookie `s` for the `startedu.pl` domain, set language cookie `l=pl-PL`,
and redirected to:

```text
https://sN.startedu.pl/Home/Client
```

An invalid login returns HTTP 200 with the login form and the validation message:

```text
Logowanie nie powiodło się. Prosimy spróbować ponownie.
```

## Read-Only Authenticated Pages

The following pages were fetched without mutating account state:

| Purpose | Path | Notes |
| --- | --- | --- |
| Dashboard | `/Home/Client` | Active child, child switch links, current month order, next month order state, today's/tomorrow's meal preview. |
| Switch child | `/User/SwitchClient/<CLIENT_ID>` | Changes the active child in the authenticated session and redirects back to the client dashboard. |
| Monthly menu/order | `/Order/Show/<ORDER_ID>` | Month calendar with meals, day classes, cancellation availability, cancelled-day markers, and order value. |
| Refunds | `/Refunds` | Current refund amount and refund transaction history. |
| Commitments | `/Commitments` | Payment obligations, payment status, due dates, paid dates, order links, and remaining amount. |
| Session keepalive | `/User/Tick` | Read-only AJAX endpoint used by the app to validate/extend the session. |

## Dashboard Data

The dashboard exposes:

- Account owner and active child labels.
- Child switch buttons via `/User/SwitchClient/<CLIENT_ID>`.
- Current month name and paid/unpaid order state.
- Current order number in display format `SE/<ORDER_ID>/<MONTH>/<YEAR>`.
- Link to `/Order/Show/<ORDER_ID>`.
- Link to `/Order/Print/<PRINT_ID>`.
- Next month state, including the unavailable-order message and planned opening
  date when ordering has not started yet.
- "Unpaid commitments" summary.

Observed next-month unavailable state:

```text
Tworzenie zamówień na nadchodzący miesiąc czerwiec nie jest jeszcze możliwe.
Planowana data uruchomienia zamówień to 25 maja 2026.
```

## Monthly Order/Menu Data

`/Order/Show/<ORDER_ID>` exposes the month calendar. Useful day-level signals:

- `div.day.green`: ordered/active day.
- `div.day.cancelled`: cancelled day.
- `data-number="<DAY>"`: day number within the month.
- `data-action="cancel-meal"`: whole-day meal cancellation is available.
- Text marker `Rezygnacja`: meal already cancelled.
- Text marker `Dzień niedostępny`: unavailable day.
- Meal component labels such as `Obiad` and `Podwieczorek`.
- Per-day price text such as `Cena: 20,50 zł`.

Days that are already in the past may still render as `green`, but lack the
`cancel-meal` action. The integration should treat cancellation availability as
an explicit flag derived from the action/button, not only from the day class.

## Refunds and Commitments Data

`/Refunds` exposes:

- Current refund amount available for automatic use against future obligations.
- Refund transaction rows with date/time, value, type, actor, and details.

`/Commitments` exposes:

- Obligation ID.
- Name, usually including month/year and StartEdu order number.
- Payment status, such as `Opłacone`.
- Due date.
- Paid date.
- Total value.
- Remaining amount due.
- Links to `Order/Show` and `Order/Print`.

## Cancellation Flow

These endpoints were discovered in the monthly order page JavaScript:

```text
POST /Order/CancelMeal?orderId=<ORDER_ID>&dayNumber=<DAY>
POST /Order/RevertMeal?orderId=<ORDER_ID>&dayNumber=<DAY>
POST /Order/CancelSingleDishType?orderId=<ORDER_ID>&dayNumber=<DAY>&dishType=<TYPE>
POST /Order/Resign?orderId=<ORDER_ID>&dayNumber=<DAY>
POST <order edit form action>
```

Only `CancelMeal` has been validated with a controlled test. `RevertMeal`,
`CancelSingleDishType`, `Resign`, and order edit endpoints were not called.

The whole-day cancellation UI is exposed by:

```html
<a data-action="cancel-meal" href="#">Odwołaj posiłek</a>
```

The page JavaScript sends:

```text
POST /Order/CancelMeal?orderId=<ORDER_ID>&dayNumber=<DAY>
X-Requested-With: XMLHttpRequest
```

The successful AJAX response observed during the controlled test was sanitized
to:

```json
{"Status": true}
```

The visible cancellation confirmation text in the web UI is:

```text
Nie będzie można cofnąć tej czynności. Czy na pewno chcesz dokonać rezygnacji z posiłku?
```

The confirmation may be bypassed when calling the AJAX endpoint directly, so any
Home Assistant action must provide its own explicit user confirmation or be
implemented only as a deliberate service call with clear documentation.

No explicit cancellation cutoff timestamp was observed in the tested HTML.
Availability appears as a permission/affordance on each day: if
`data-action="cancel-meal"` is absent, the integration must treat the cutoff or
permission window as closed and must not call `CancelMeal`.

## Controlled Cancellation Test

On 2026-05-26 at 08:18 Europe/Warsaw, a test account child and May 2026 order
were used to validate whole-day cancellation. The issue comment for
`patrykchoros/startedu-ha#7` contains the sanitized evidence.

Preconditions for both 2026-05-26 and 2026-05-27:

- Day block existed in `/Order/Show/<ORDER_ID>`.
- Day class was `green`.
- `data-action="cancel-meal"` was present.
- `Rezygnacja` marker was absent.
- Meal labels were `Obiad` and `Podwieczorek`.

For each day, exactly one `CancelMeal` request was sent. Both requests returned
HTTP 200 and JSON `Status: true`.

Postconditions after refreshing `/Order/Show/<ORDER_ID>`:

- Day class became `cancelled`.
- `Rezygnacja` marker was present.
- `data-action="cancel-meal"` was absent.
- The cancellation applied to the full daily meal set, not an individual dish.

## Cancellation Failure Modes and Safety Rules

Future implementation must treat cancellation as unsafe unless all preconditions
are freshly verified immediately before the POST:

- The selected child is active or the request has switched to that child and
  reloaded the target order.
- The target date belongs to the visible order month.
- The day block exists and is not already `cancelled`.
- The day is not marked unavailable, disabled, or `Dzień niedostępny`.
- `data-action="cancel-meal"` is present.
- The day has at least one non-cancelled meal slot.

The implementation must surface these failure states without attempting the
mutation:

- Missing target child, order, or day block.
- Missing cancellation action.
- Day already cancelled.
- Day unavailable or not ordered.
- Session expired or authentication failed.
- StartEdu returned HTTP 4xx/5xx.
- AJAX response was not JSON, omitted `Status`, or returned `Status: false`.
- Post-refresh did not show `cancelled` and `Rezygnacja`.

After a successful cancellation, the integration must refresh StartEdu data
immediately before updating Home Assistant entities.
