# ParentOS for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Go-Pomegranate&repository=homeassistant-parentos&category=integration)

Custom integration that brings your [ParentOS](https://parentos.ai) family data into Home Assistant.

## Features

- **Day State** — family day status (calm / moderate / busy / full)
- **Calendar** — native HA calendar entity with all family events
- **Energy** — per-member energy levels and mood
- **Tasks** — overdue and pending task counts
- **Health** — medication tracking status (metadata only, no PII)
- **Finance** — tracking engagement status (metadata only, no PII)
- **Baseline** — family pace trend over time

All data is read-only. No personal health/financial details are exposed — only aggregate metadata and counts.

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
   - `wellness:read`
   - `family:read`
   - `calendar:read`
2. In Home Assistant, go to **Settings → Devices & Services → Add Integration**
3. Search for **ParentOS**
4. Enter your API URL and developer token (`pt_...`)

## Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.parentos_day_state` | Family day state | calm/moderate/busy/full |
| `sensor.parentos_events_today` | Number of events today | count |
| `sensor.parentos_busy_minutes` | Busy minutes today | min |
| `sensor.parentos_next_event` | Next event title | — |
| `sensor.parentos_next_event_minutes` | Minutes until next event | min |
| `sensor.parentos_longest_free_slot` | Longest free slot | min |
| `sensor.parentos_conflict_count` | Calendar conflicts | count |
| `sensor.parentos_family_pace` | Family pace baseline | slow/medium/fast |
| `sensor.parentos_baseline_trend` | Pace trend direction | up/down/stable |
| `sensor.parentos_health_status` | Health tracking status | — |
| `sensor.parentos_medications_tracked` | Medications tracked | count |
| `sensor.parentos_finance_engagement` | Finance tracking status | — |
| `sensor.parentos_tasks_overdue` | Overdue tasks | count |
| `sensor.parentos_tasks_pending_today` | Tasks due today | count |

## Calendar

The integration creates a native `calendar.parentos_family_calendar` entity that shows all family events from ParentOS. Works with HA calendar card and automations.

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
```

## Privacy

This integration only accesses **aggregate metadata** — event counts, status labels, and scores. No personal health records, financial transactions, or encrypted data is exposed. All communication uses developer tokens with scope-based access control.

**Note:** Calendar event titles and locations are visible in the HA dashboard, state history, and automations. If your calendar contains sensitive entries (e.g. medical appointments), consider using ParentOS server-side calendar filters to control which events are shared via the HA API.

## RESTful Sensor Alternative

If you prefer a simpler setup without HACS, you can use HA's built-in REST integration:

```yaml
rest:
  - resource: https://api.parentos.ai/api/ha/v1/snapshot
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
