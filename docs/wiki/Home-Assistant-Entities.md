# Home Assistant Entities

Each StartEdu child is represented as a separate Home Assistant device. See
`docs/home-assistant-entity-model.md` for the source specification.

## Entity Map

```mermaid
flowchart TD
    entry["StartEdu config entry"] --> account["Main StartEdu device"]
    account --> refresh["Diagnostic refresh button"]
    account --> sync["Sync status sensors"]
    entry --> coordinator["Shared coordinator cache"]
    coordinator --> child["Child device"]

    child --> calendar["Meal calendar"]
    child --> menu["Menu sensors"]
    child --> status["Status and accounting sensors"]
    child --> binary["Food and cancellation binary sensors"]
    child --> actions["Cancellation buttons"]

    calendar --> cal_entity["calendar.<child>_meals"]
    menu --> day_menu["today/tomorrow menu sensors"]
    status --> order_state["order, refund, unpaid, update sensors"]
    binary --> food["has_food today/tomorrow"]
    binary --> can_cancel["can_cancel today/tomorrow"]
    actions --> cancel_buttons["cancel today/tomorrow meals"]
```

## Calendar

- `calendar.<child>_meals`: meal slots as calendar events.

Cancelled meal events use a localized summary prefix because Home Assistant
calendar events do not expose a native cancelled/status field. The original
StartEdu meal label is kept unchanged, for example `CANCELLED: Obiad` in English
or `ODWOŁANE: Obiad` in Polish. Event descriptions contain only normalized menu
text. Unknown Home Assistant languages fall back to English.

## Sensors

Main StartEdu device:

- `sensor.<entry>_sync_status`
- `sensor.<entry>_last_sync_status`
- `sensor.<entry>_last_sync_time`

`sync_status` shows whether a refresh is waiting or running.
`last_sync_status` shows the result of the last completed refresh attempt.
`last_sync_time` is updated after both successful and failed refresh attempts.
Display states are localized to the Home Assistant language.

Child devices:

- `sensor.<child>_today_menu`
- `sensor.<child>_tomorrow_menu`
- `sensor.<child>_today_meal_status`
- `sensor.<child>_tomorrow_meal_status`
- `sensor.<child>_last_successful_update`
- `sensor.<child>_current_month_order_status`
- `sensor.<child>_next_month_order_status`
- `sensor.<child>_refund_available`
- `sensor.<child>_unpaid_amount`
- `sensor.<child>_next_order_opening_date`

Menu attributes include localized `status` values for display and stable
`status_code` values for automations. Meal attributes intentionally avoid raw
StartEdu HTML, cookies, credentials, and internal child/meal identifiers.

## Binary Sensors

- `binary_sensor.<child>_has_food_today`
- `binary_sensor.<child>_has_food_tomorrow`
- `binary_sensor.<child>_can_cancel_today_meal`
- `binary_sensor.<child>_can_cancel_tomorrow_meal`
- `binary_sensor.<child>_next_month_ordering_available`

## Buttons

- `button.<entry>_refresh_startedu_data`
- `button.<child>_cancel_today_meals`
- `button.<child>_cancel_tomorrow_meals`

The refresh button is diagnostic and user-triggered. It requests a full StartEdu
coordinator refresh for the configured account rather than refreshing current
and next-month data separately.

The child-device cancellation buttons cancel the whole daily meal set for the
selected child and local day. They are available only when the current
coordinator data says that today's or tomorrow's meal can be cancelled. Pressing
one still runs the guarded StartEdu flow with a fresh pre-refresh and
post-confirmation.

Entity names may vary based on Home Assistant's entity registry and translation
handling.

## Cancellation Service

The first mutating interface is an explicit service call:

```text
startedu.cancel_meal
```

It targets one child and one local date. Before calling StartEdu, the integration
refetches the target order and verifies that the day still exposes `can_cancel`.
After a successful `CancelMeal` response, the coordinator is updated only after
the refreshed day is `cancelled`, shows `Rezygnacja`, and no longer exposes the
cancel action.

```mermaid
flowchart TD
    service["User calls startedu.cancel_meal"]
    service --> target["Resolve account,\nchild, and local date"]
    target --> prefetch["Refresh target order"]
    prefetch --> decision{"Day can be cancelled?"}
    decision -- "No" --> refuse["Refuse without\ncalling StartEdu"]
    decision -- "Yes" --> post["POST CancelMeal\none whole day"]
    post --> confirm["Refresh and confirm\ncancelled state"]
    confirm --> ok{"Confirmed?"}
    ok -- "No" --> error["Raise error and keep\nold coordinator data"]
    ok -- "Yes" --> cache["Publish confirmed data\nto coordinator cache"]
    cache --> entities["Entities update from\nconfirmed snapshot"]
```

Home Assistant button entities do not provide a native confirmation prompt
before `button.press`. Safety therefore comes from clear naming, availability
state, fresh pre-validation, and post-refresh confirmation.
