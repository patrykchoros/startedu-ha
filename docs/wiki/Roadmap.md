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

- Identify cancellation endpoint or form flow.
- Confirm deadline rules and user-visible failure states.
- Design a Home Assistant action only after the flow is safe and reversible
  enough for automation.

