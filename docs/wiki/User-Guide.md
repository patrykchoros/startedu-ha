# StartEdu User Guide

This guide is for Home Assistant users who already have the StartEdu
integration added and want to use the entities safely day to day.

## What You Will See

The integration creates one main StartEdu device and one device for each child
found in StartEdu.

The main StartEdu device contains account-level controls and diagnostics:

- `button.<entry>_refresh_startedu_data`: fetches fresh data from StartEdu.
- `sensor.<entry>_sync_status`: shows whether a refresh is waiting or running.
- `sensor.<entry>_last_sync_status`: shows whether the last refresh succeeded
  or failed.
- `sensor.<entry>_last_sync_time`: shows when the last refresh attempt ended.

Each child device contains meal entities:

- `calendar.<child>_meals`: ordered and cancelled meals as calendar events.
- `sensor.<child>_today_menu`: today's menu summary.
- `sensor.<child>_tomorrow_menu`: tomorrow's menu summary.
- `sensor.<child>_today_meal_status`: today's meal status.
- `sensor.<child>_tomorrow_meal_status`: tomorrow's meal status.
- `binary_sensor.<child>_has_food_today`: on when the child has food today.
- `binary_sensor.<child>_has_food_tomorrow`: on when the child has food
  tomorrow.
- `binary_sensor.<child>_can_cancel_today_meal`: on when today's meal can still
  be cancelled.
- `binary_sensor.<child>_can_cancel_tomorrow_meal`: on when tomorrow's meal can
  still be cancelled.
- `button.<child>_cancel_today_meals`: cancels the whole meal set for today.
- `button.<child>_cancel_tomorrow_meals`: cancels the whole meal set for
  tomorrow.

Some accounts also expose:

- `sensor.<child>_refund_available`: refund amount visible in StartEdu.
- `sensor.<child>_unpaid_amount`: unpaid amount visible in StartEdu.
- `sensor.<child>_current_month_order_status`: current month order status.
- `sensor.<child>_next_month_order_status`: next month order status.
- `binary_sensor.<child>_next_month_ordering_available`: whether StartEdu shows
  next-month ordering as available.
- `sensor.<child>_next_order_opening_date`: when StartEdu says next ordering
  should open.

Entity IDs may differ in your Home Assistant because Home Assistant creates
them from the child names and your entity registry.

## Common States

Meal and order states are localized by Home Assistant language. These are the
stable meanings behind the visible labels:

- `paid`: the meal or order is paid.
- `cancelled`: the meal day has been cancelled in StartEdu.
- `unpaid`: payment is still due.
- `not_ordered`: no meal was ordered for that day.
- `no_school`: StartEdu marks the day as unavailable, disabled, or no school.
- `available`: ordering is available.
- `blocked`: ordering is not yet available.
- `unknown`: StartEdu did not expose enough information to decide safely.

`has_food_*` is on only for paid, non-cancelled meals. A cancelled day can still
have a menu in the calendar or menu sensor, but `has_food_*` will be off.

## Refreshing Data

StartEdu menus are monthly, so the integration does not need to fetch data very
often. The default automatic polling interval is once per day. The integration
also performs one morning refresh around `09:00` local time so today's
cancellation availability does not stay stale after StartEdu closes the
cancellation window.

Use `button.<entry>_refresh_startedu_data` when you know something changed in
StartEdu and you want Home Assistant to update now. A manual refresh fetches
all children and all currently discoverable current/next-month data.

If refresh fails, check the main StartEdu device:

- `sync_status` should return to waiting after the attempt.
- `last_sync_status` shows whether the last attempt failed.
- `last_sync_time` shows when the attempt ended.

## Cancelling Meals

The easiest way to cancel meals is from the child device:

- Press `button.<child>_cancel_today_meals` to cancel today's whole meal set.
- Press `button.<child>_cancel_tomorrow_meals` to cancel tomorrow's whole meal
  set.

Each button is available only when the current Home Assistant data says the day
can still be cancelled. Pressing a button still checks StartEdu again before
doing anything. If StartEdu no longer allows cancellation, the integration
stops without sending the cancellation request.

Cancellation safety rules:

- The integration cancels the whole day, not one dish or one menu component.
- The integration does not undo cancellations.
- The integration does not place orders.
- The integration calls only the validated `CancelMeal` flow.
- After StartEdu accepts cancellation, the integration refreshes again and
  updates Home Assistant only after the cancelled state is confirmed.

Home Assistant button entities do not show a built-in confirmation prompt.
Treat the cancellation buttons like real actions that change StartEdu data.

## Advanced Cancellation Service

The `startedu.cancel_meal` action remains available for advanced scripts and
automations. It needs:

- `config_entry_id`: the StartEdu config entry to use.
- `child_id`: the internal StartEdu child identifier.
- `date`: the local Home Assistant date to cancel.

Example shape:

```yaml
action: startedu.cancel_meal
data:
  config_entry_id: "01HVEXAMPLESTARTEDU"
  child_id: "CLIENT_ID_1"
  date: "2026-05-28"
```

Prefer the child-device buttons for normal use. Use the service only when you
are comfortable with Home Assistant's internal IDs and you have added clear
conditions to avoid accidental cancellation.

## Dashboard Example

Replace entity IDs with the ones Home Assistant created for your child.

```yaml
type: entities
title: StartEdu meals
entities:
  - sensor.child_today_menu
  - sensor.child_today_meal_status
  - binary_sensor.child_has_food_today
  - binary_sensor.child_can_cancel_today_meal
  - button.child_cancel_today_meals
  - sensor.child_tomorrow_menu
  - sensor.child_tomorrow_meal_status
  - binary_sensor.child_has_food_tomorrow
  - binary_sensor.child_can_cancel_tomorrow_meal
  - button.child_cancel_tomorrow_meals
```

For the main StartEdu device, a small diagnostic card is useful:

```yaml
type: entities
title: StartEdu sync
entities:
  - button.startedu_refresh_startedu_data
  - sensor.startedu_sync_status
  - sensor.startedu_last_sync_status
  - sensor.startedu_last_sync_time
```

## Automation Examples

A safe first automation is a notification, not automatic cancellation:

```yaml
alias: StartEdu reminder when tomorrow can be cancelled
triggers:
  - trigger: time
    at: "18:00:00"
conditions:
  - condition: state
    entity_id: binary_sensor.child_can_cancel_tomorrow_meal
    state: "on"
actions:
  - action: notify.mobile_app_phone
    data:
      title: StartEdu
      message: Tomorrow's meal can still be cancelled if needed.
```

If you build a cancellation automation, keep it manual or add strict
conditions. Avoid blind automatic cancellation based only on time.

```yaml
alias: StartEdu manual script to cancel tomorrow
sequence:
  - condition: state
    entity_id: binary_sensor.child_can_cancel_tomorrow_meal
    state: "on"
  - action: button.press
    target:
      entity_id: button.child_cancel_tomorrow_meals
mode: single
```

## Troubleshooting

If menu data looks stale, press the refresh button on the main StartEdu device.

If cancellation buttons are unavailable, StartEdu may no longer expose the
cancel action for that day, the day may already be cancelled, or the day may not
have an ordered meal.

If only some entities have values, check `last_sync_status` and Home Assistant
logs for StartEdu integration messages. Do not share logs publicly without
checking that they do not include private data.
