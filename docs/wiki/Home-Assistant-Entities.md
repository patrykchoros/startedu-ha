# Home Assistant Entities

Each StartEdu child is represented as a separate Home Assistant device. See
`docs/home-assistant-entity-model.md` for the source specification.

## Calendar

- `calendar.<child>_meals`: meal slots as calendar events.

Cancelled meal events use the `ODWOŁANE:` summary prefix because Home Assistant
calendar events do not expose a native cancelled/status field.

## Sensors

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

## Binary Sensors

- `binary_sensor.<child>_has_food_today`
- `binary_sensor.<child>_has_food_tomorrow`
- `binary_sensor.<child>_can_cancel_today_meal`
- `binary_sensor.<child>_can_cancel_tomorrow_meal`
- `binary_sensor.<child>_next_month_ordering_available`

Entity names may vary based on Home Assistant's entity registry and translation
handling.
