# Synchronization Strategy

StartEdu meal plans are monthly, so the integration avoids frequent automatic
polling. The default automatic polling interval is one day, with one additional
daily morning refresh for same-day cancellation availability.

## Refresh Flow

The key rule is that only selected triggers fetch StartEdu again. Daily rollovers
and meal time changes only recalculate Home Assistant entities from the cached
StartEdu snapshot.

```mermaid
flowchart TD
    setup["Config entry setup\nHA startup or reload"] --> full
    reauth["Successful reauthentication"] --> full
    poll["Configured polling interval\n60-1440 minutes"] --> full
    cancel_window["Daily cancellation availability\n09:00 local"] --> full
    month["Local month boundary"] --> full
    opening["next_order_opening_date"] --> full
    manual["Refresh button"] --> full

    cancel_buttons["Child cancellation buttons"] --> mutation
    cancel["startedu.cancel_meal"] --> mutation
    mutation["Mutating StartEdu request\nwith post-refresh confirmation"] --> publish

    full["Full StartEdu refresh"] --> fetch
    fetch["Fetch account, children,\ncurrent and next-month orders"] --> cache
    cache["Coordinator cache"] --> publish

    midnight["Local midnight"] --> local
    options["Meal time or polling\noptions changed"] --> local
    local["Local recalculation only\nno StartEdu request"] --> notify

    publish["Publish fresh account snapshot"] --> entities
    notify["Notify entities"] --> entities
    entities["Calendar, sensors,\nbinary sensors, button state"]
```

## Automatic Refresh

The coordinator refreshes StartEdu data when the config entry is set up, on
Home Assistant startup or reload, after successful reauthentication, on the
configured polling interval, once each morning at `09:00` local time to refresh
today's cancellation availability, at the local month boundary, on the next
future `next_order_opening_date` exposed by StartEdu, and after successful
mutating actions such as meal cancellation.

The polling interval is configurable and clamped between `60` and `1440`
minutes.

The morning cancellation refresh exists because StartEdu does not expose a
separate cutoff timestamp. The integration can only know whether today's meal is
still cancellable by re-reading the order page and checking whether
`data-action="cancel-meal"` is still present.

## Local Recalculation

Today/tomorrow entities and calendar event times are derived from cached StartEdu
data plus local Home Assistant state. At local midnight, the coordinator
notifies entities without fetching StartEdu. Same-day cancellation availability
is not recalculated locally after the morning cutoff window, because that state
comes from StartEdu page actions. Changing meal time options updates the
coordinator interval and notifies entities without reloading the config entry or
fetching StartEdu.

## Manual Refresh

The integration exposes one diagnostic refresh button:

```text
button.<entry>_refresh_startedu_data
```

It requests a full coordinator refresh for the StartEdu account, including all
child accounts and current/next-month data when StartEdu exposes it. Separate
current-month and next-month refresh buttons are intentionally not exposed.
