# Project Overview

StartEdu for Home Assistant is a HACS custom integration that exposes data from
the StartEdu meal platform as Home Assistant entities.

The MVP is read-mostly:

- A meal calendar for upcoming StartEdu meals.
- Sensors for the next meal, account values when available, and synchronization
  health.
- A UI config flow for credentials and polling options.
- An explicit `startedu.cancel_meal` service for whole-day cancellation.

Meal cancellation research has confirmed the whole-day StartEdu `CancelMeal`
flow. The implemented service keeps cancellation user-triggered, refreshes and
validates before the request, and updates Home Assistant only after post-action
confirmation.
