# ParentOS for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Go-Pomegranate/homeassistant-parentos)](https://github.com/Go-Pomegranate/homeassistant-parentos/releases)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Go-Pomegranate&repository=homeassistant-parentos&category=integration)

Custom integration that brings your [ParentOS](https://parentos.ai) family data into Home Assistant.

## Features

- **Day State** — family day status (calm / moderate / busy / full)
- **Calendar** — native HA calendar entity with all family events
- **Shopping Lists** — full todo entities with add, check off, and delete support
- **Meal Plan** — today's planned meals with breakfast/lunch/dinner/snack breakdown
- **Family Members** — per-member sensors with status, role, age, and avatar
- **Tasks** — overdue and pending task counts
- **Health** — medication tracking status (metadata only, no PII)
- **Finance** — tracking engagement status (metadata only, no PII)
- **Baseline** — family pace and trend over time
- **Dashboard Templates** — ready-made YAML dashboards (native + Mushroom cards)

Shopping lists and family members are **dynamic** — new lists/members appear automatically, deleted ones are removed. No restart needed.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/Go-Pomegranate/homeassistant-parentos` with category **Integration**
4. Search for "ParentOS" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/parentos/` to your `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. In ParentOS, go to **Settings → Developer Tokens** and create a token with these scopes:
   - `wellness:read` — day state, energy, health, baseline
   - `family:read` — family members, tasks
   - `calendar:read` — calendar events
   - `meals:read` — shopping lists, meal plan
   - `meals:write` — shopping list CRUD (add/edit/delete items)
2. In Home Assistant, go to **Settings → Devices & Services → Add Integration**
3. Search for **ParentOS**
4. Enter your API URL and developer token (`pt_...`)

## Entities

### Sensors

| Entity ID | Description | Unit |
|-----------|-------------|------|
| `sensor.parentos_day_state` | Family day state | calm/moderate/busy/full |
| `sensor.parentos_attention_needed` | Attention needed flag | True/False |
| `sensor.parentos_events_today` | Events today | count |
| `sensor.parentos_busy_minutes` | Busy minutes today | min |
| `sensor.parentos_next_event` | Next event title | text |
| `sensor.parentos_next_event_in` | Minutes until next event | min |
| `sensor.parentos_longest_free_slot` | Longest free slot | min |
| `sensor.parentos_calendar_conflicts` | Calendar conflicts | count |
| `sensor.parentos_family_pace` | Family pace | slow/medium/fast |
| `sensor.parentos_pace_trend` | Pace trend direction | up/down/stable |
| `sensor.parentos_health_tracking` | Health tracking status | active/not_started |
| `sensor.parentos_medications_tracked` | Medications tracked | count |
| `sensor.parentos_finance_tracking` | Finance tracking status | active/basic/not_started |
| `sensor.parentos_overdue_tasks` | Overdue tasks | count |
| `sensor.parentos_tasks_today` | Tasks due today | count |
| `sensor.parentos_meal_plan_today` | Meals planned today | count |

The **Meal Plan** sensor has extra attributes: `breakfast`, `lunch`, `dinner`, `snack`, `next_meal`.

### Calendar

`calendar.parentos_family_calendar` — native HA calendar with all family events. Works with calendar card and automations.

### Shopping Lists (Todo)

`todo.parentos_{list_name}` — one entity per active shopping list. Supports:
- Add items from HA todo card
- Check off / uncheck items
- Delete items
- Item descriptions (quantity, category, store, notes)

### Family Members

`sensor.parentos_{member_name}` — one sensor per family member. State shows health status. Attributes: `role`, `age`, `picture`.

## Dashboard Templates

Ready-made dashboard YAML files are in the `dashboards/` directory:

| File | Description | Requirements |
|------|-------------|--------------|
| `parentos-overview.yaml` | Native HA cards | None |
| `parentos-mushroom.yaml` | Mushroom cards | [Mushroom](https://github.com/piitaya/lovelace-mushroom) (HACS) |

**To use:** Open your dashboard → Edit → Raw Configuration Editor → paste the YAML content.

## Automation Examples

```yaml
# Notify when day becomes busy
automation:
  - trigger:
      - platform: state
        entity_id: sensor.parentos_day_state
        to: "busy"
    action:
      - service: notify.mobile_app
        data:
          message: "Family day is getting busy — {{ states('sensor.parentos_events_today') }} events today"

# Dim lights when family energy is low
automation:
  - trigger:
      - platform: state
        entity_id: sensor.parentos_day_state
        to: "full"
    action:
      - service: light.turn_on
        target:
          area_id: living_room
        data:
          brightness_pct: 40
          color_temp_kelvin: 2700

# Remind about shopping when leaving home
automation:
  - trigger:
      - platform: zone
        entity_id: person.you
        zone: zone.home
        event: leave
    condition:
      - condition: numeric_state
        entity_id: todo.parentos_grocery_list
        attribute: incomplete_count
        above: 0
    action:
      - service: notify.mobile_app
        data:
          message: "You have items on your grocery list!"
```

## Privacy

This integration only accesses **aggregate metadata** — event counts, status labels, and scores. No personal health records, financial transactions, or encrypted data is exposed. All communication uses developer tokens with scope-based access control.

**Note:** Calendar event titles and locations are visible in the HA dashboard, state history, and automations. If your calendar contains sensitive entries (e.g. medical appointments), consider using ParentOS server-side calendar filters to control which events are shared via the HA API.

## RESTful Sensor Alternative

If you prefer a simpler setup without HACS, you can use HA's built-in REST integration:

```yaml
rest:
  - resource: https://app.parentos.ai/api/ha/v1/snapshot
    scan_interval: 300
    headers:
      Authorization: "Bearer pt_YOUR_TOKEN"
    sensor:
      - name: "ParentOS Day State"
        value_template: "{{ value_json.dayState }}"
      - name: "ParentOS Events Today"
        value_template: "{{ value_json.calendar.eventsToday }}"
```

## License

MIT
