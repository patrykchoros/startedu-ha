# Roadmap

## Milestone 1: Repository and HACS Scaffold

- Create the private GitHub repository.
- Add the HACS metadata and custom integration structure.
- Add CI checks for parser tests and static syntax validation.

## Milestone 2: StartEdu Read-Only Data

- Validate login with a test account.
- Document the authenticated pages or endpoints used by StartEdu.
- Parse meals, balance, refunds, and synchronization state from sanitized
  fixtures.

## Milestone 3: Home Assistant Entities

- Expose `calendar.startedu_meals`.
- Expose sensors for next meal, balance, refunds, sync status, and last
  successful update.
- Add Home Assistant integration tests around config flow, coordinator, and
  entity behavior.

## Milestone 4: Meal Cancellation Research

- Identify cancellation endpoint or form flow. Completed for whole-day
  `CancelMeal` through issue #7.
- Confirm deadline rules and user-visible failure states. Completed for the
  observed flow: cancellation availability is represented by the per-day cancel
  action, and missing action, already-cancelled, unavailable, failed HTTP/JSON,
  and failed post-refresh states are documented as implementation guards.
- Design a Home Assistant action only after the flow is safe enough for
  user-triggered automation.

## Milestone 5: Meal Cancellation Implementation

- Implement `startedu.cancel_meal` as an explicit service call.
- Revalidate child, order, date, and cancellation availability immediately
  before sending the request.
- Refresh StartEdu data immediately after successful cancellation.
- Keep cancellation buttons out of the first mutating implementation.
