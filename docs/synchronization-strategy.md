# Synchronization Strategy

StartEdu meal plans are monthly, so the integration should avoid frequent
automatic polling. The default automatic refresh interval is one day.

## Automatic Refresh

The coordinator refreshes StartEdu data:

- when the config entry is first set up;
- on Home Assistant startup or config entry reload;
- after successful reauthentication;
- on the configured polling interval, defaulting to `1440` minutes;
- at the local month boundary;
- on the next future `next_order_opening_date` exposed by StartEdu;
- after a future successful mutating action, such as meal cancellation.

The configurable polling interval is clamped between `60` and `1440` minutes.
This keeps advanced users in control while discouraging excessive StartEdu
requests.

## Local Recalculation

Some changes should update Home Assistant entities without fetching StartEdu:

- Today/tomorrow entity values are derived from the cached StartEdu snapshot and
  the current local date.
- At local midnight the coordinator notifies entities so today/tomorrow values
  roll over without fetching StartEdu.
- Meal time option changes are applied locally. Calendar event times use the
  latest options, so changing lunch or snack time does not require StartEdu data
  to change.
- Updating options changes the coordinator polling interval and notifies
  entities without reloading the config entry.

## Manual Refresh

The integration exposes a single diagnostic button:

```text
button.<entry>_refresh_startedu_data
```

Pressing it requests a full coordinator refresh for the StartEdu account. The
refresh covers all child accounts and all currently discoverable relevant order
pages, including current and next-month data when StartEdu exposes it. Separate
current-month and next-month refresh buttons are intentionally not exposed,
because a single full refresh avoids mixed stale/fresh states.
