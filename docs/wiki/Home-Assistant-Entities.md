# Home Assistant Entities

## Calendar

- `calendar.startedu_meals`: all known upcoming and historical meal entries in
  the current StartEdu snapshot.

## Sensors

- `sensor.startedu_next_meal`: summary of the nearest upcoming meal.
- `sensor.startedu_balance`: account balance in PLN when available.
- `sensor.startedu_refunds`: refund value in PLN when available.
- `sensor.startedu_last_successful_update`: timestamp of the latest successful
  fetch.
- `sensor.startedu_sync_status`: simple synchronization health state.

Entity names may vary based on Home Assistant's entity registry and translation
handling.

