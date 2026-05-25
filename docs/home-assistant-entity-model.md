# Home Assistant Entity Model

This document defines the target entity model for StartEdu. It is based on the
read-only discovery notes in `docs/startedu-flow-discovery.md` and focuses on
future Home Assistant usefulness before cancellation actions are implemented.

## Device Model

Each StartEdu child is represented as a separate Home Assistant device.

- Device identifier: `(startedu, <config_entry_id>, <client_id>)`
- Device name: child display name from StartEdu
- Device manufacturer: `StartEdu`

All child-specific entities belong to the child device. This keeps dashboards
and automations clear for multi-child accounts.

## Calendar

Each child gets one calendar:

```text
calendar.<child>_meals
```

Calendar rules:

- Every meal slot is a separate event.
- Supported slot types are `breakfast`, `lunch`, `afternoon_snack`, and `other`.
- Event summary is the meal slot name, such as `Obiad`.
- Cancelled event summary uses the prefix `ODWOŁANE:`, such as `ODWOŁANE: Obiad`.
- Event description contains full menu, status, meal type, price, order number,
  child name, and cancellation availability.
- Event start/end times come from integration options.

Home Assistant `CalendarEvent` does not expose a native cancelled/status field,
so cancelled meals are represented through the `ODWOŁANE:` title prefix and
event description.

## Automation Entities

Each child gets automation-friendly entities.

Menu sensors:

- `sensor.<child>_today_menu`
- `sensor.<child>_tomorrow_menu`

The sensor state is a short menu summary kept below Home Assistant's state
length limit. Full menu data is exposed in attributes:

- `full_menu`
- `meal_slots`
- `date`
- `status`
- `order_number`
- `order_numbers`
- `is_cancelled`

Binary sensors:

- `binary_sensor.<child>_has_food_today`
- `binary_sensor.<child>_has_food_tomorrow`
- `binary_sensor.<child>_can_cancel_today_meal`
- `binary_sensor.<child>_can_cancel_tomorrow_meal`
- `binary_sensor.<child>_next_month_ordering_available`

Status/accounting sensors:

- `sensor.<child>_today_meal_status`
- `sensor.<child>_tomorrow_meal_status`
- `sensor.<child>_last_successful_update`
- `sensor.<child>_current_month_order_status`
- `sensor.<child>_next_month_order_status`
- `sensor.<child>_refund_available`
- `sensor.<child>_unpaid_amount`
- `sensor.<child>_next_order_opening_date`

Meal status states:

- `not_ordered`
- `unpaid`
- `paid`
- `cancelled`
- `no_school`
- `unknown`

`has_food_*` is true only when the day has a paid, non-cancelled meal slot.

## Options

Meal times are configured in integration options and interpreted in Home
Assistant local time.

| Option | Default | Duration |
| --- | --- | --- |
| `breakfast_time` | `08:00` | 30 minutes |
| `lunch_time` | `12:00` | 45 minutes |
| `afternoon_snack_time` | `14:30` | 30 minutes |
| `other_meal_time` | `12:00` | 30 minutes |

Unknown StartEdu meal labels use `other_meal_time` and keep the original label
in attributes.

## Future Cancellation Actions

Cancellation remains blocked by issue #7. The test account must not be used to
cancel meals.

Planned future actions:

- `startedu.cancel_today_meal`
- `startedu.cancel_tomorrow_meal`
- `button.<child>_cancel_today_meal`
- `button.<child>_cancel_tomorrow_meal`

These should be implemented only after endpoint safety, confirmation behavior,
failure handling, and child targeting are validated.

