# Project Overview

StartEdu for Home Assistant is a HACS custom integration that exposes data from
the StartEdu meal platform as Home Assistant entities.

The MVP is read-only:

- A meal calendar for upcoming StartEdu meals.
- Sensors for the next meal, account values when available, and synchronization
  health.
- A UI config flow for credentials and polling options.

Meal cancellation is intentionally deferred until the authenticated StartEdu
flow, cutoff rules, and failure modes are documented with a test account.

