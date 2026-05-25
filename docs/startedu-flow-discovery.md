# StartEdu Login and Data-Fetch Flow

Discovery date: 2026-05-25.

This document records the authenticated read-only flow observed with the shared
test account. The account is used only for discovery. Do not place orders,
cancel meals, revert cancellations, or confirm any modal that mutates StartEdu
state.

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

## Mutating Endpoints Discovered but Not Called

These endpoints were discovered by reading JavaScript only. They must not be
called while using the shared test account:

```text
POST /Order/CancelMeal?orderId=<ORDER_ID>&dayNumber=<DAY>
POST /Order/RevertMeal?orderId=<ORDER_ID>&dayNumber=<DAY>
POST /Order/CancelSingleDishType?orderId=<ORDER_ID>&dayNumber=<DAY>&dishType=<TYPE>
POST /Order/Resign?orderId=<ORDER_ID>&dayNumber=<DAY>
POST <order edit form action>
```

The visible cancellation confirmation text is:

```text
Nie będzie można cofnąć tej czynności. Czy na pewno chcesz dokonać rezygnacji z posiłku?
```

Future cancellation work must use a separate safety plan and must not reuse this
read-only discovery account for actual cancellations.

