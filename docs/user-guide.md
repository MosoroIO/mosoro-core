# Mosoro Dashboard — User Guide

## Overview

The Mosoro dashboard is the control plane for your connected robot fleet. It provides real-time visibility and control over all robots managed by the Mosoro communications bridge.

---

## Getting Started

### Demo Mode (no robots required)

```bash
git clone https://github.com/mosoroio/mosoro-core.git
cd mosoro-core
make demo
# Open http://localhost:3000
```

Three virtual robots will appear immediately. No configuration needed.

Default credentials: `admin` / `admin`

### Connect Real Robots

```bash
make setup
```

The interactive wizard will walk you through selecting adapters, entering robot connection details, and generating your configuration.

---

## Dashboard Screens

### Dashboard — Fleet Overview (`/`)

The home screen. Shows a real-time summary of your fleet:
- Total robots, online/offline counts
- Breakdown by vendor and status
- Fleet table with sortable columns

### Robots (`/robots`)

Full list of all robots with status, battery, health, and last-update time.

- Click any robot to open its detail page
- Sort by any column
- Filter by status or search by robot ID

### Robot Detail (`/robots/:id`)

Full status view for a single robot:
- Position (X, Y, heading)
- Battery percentage and health
- Current task and progress
- Recent events from this robot

### Map (`/map`)

2D coordinate map of all robots with known positions.

- **Zoom:** mouse wheel or pinch on mobile
- **Pan:** click and drag
- **Color by:** vendor or status (dropdown)
- **Hover** a robot to see ID, status, battery, and position
- **Click** a robot to open its detail page
- **Reset View:** returns to default zoom and center

> The map auto-scales to fit all robot positions. Robots appear only if their adapter reports position data.

### Tasks (`/tasks`)

Send a command to any online robot.

| Field | Description |
|---|---|
| Robot | Select from currently online robots |
| Action | `move_to`, `pick`, `dock`, `pause`, `resume` |
| Position (optional) | Target X/Y/Z coordinates for movement commands |
| Parameters (optional) | JSON object for action-specific options |

### Events (`/events`)

Live stream of all MQTT messages received from the fleet. Shows robot ID, vendor, topic, and raw payload.

### Notifications

The bell icon (🔔) in the top bar shows fleet alerts:
- Robot went offline
- Robot entered error state

Click the bell to open the notification panel. Notifications also appear as toasts and (if permitted) as browser push notifications when the tab is in the background.

To receive alerts via webhook (Slack, PagerDuty, email, etc.), set `NOTIFY_WEBHOOK_URL` in your `.env`.

### Extensions (`/extensions`)

Browse available robot adapters and premium add-ons.

**Robot Adapters** (free) — install the adapter for each vendor in your facility.

**Platform Features** — premium capabilities available with a Mosoro Pro subscription.

---

## Adding Robots

1. Run `make setup` to launch the interactive wizard, or
2. Manually add the robot to `robots.yaml` (see [`robots.yaml.example`](../robots.yaml.example)) and restart the agent: `docker compose restart agent`

The robot will appear in the dashboard within seconds of the adapter connecting.

## Removing Robots

Remove the robot's entry from `robots.yaml` and restart the agent:

```bash
docker compose restart agent
```

---

## Keyboard Shortcuts

Press `⌘K` (Mac) or `Ctrl+K` (Windows/Linux) to open the command palette for quick navigation.

---

## Configuration Reference

| Variable | Description | Default |
|---|---|---|
| `MQTT_BROKER_HOST` | MQTT broker hostname | `mosquitto` |
| `MQTT_BROKER_PORT` | MQTT broker port (1883 plain, 8883 TLS) | `1883` |
| `MOSORO_ADMIN_USERNAME` | Dashboard login username | `admin` |
| `MOSORO_ADMIN_PASSWORD` | Dashboard login password | `changeme-dev` |
| `NOTIFY_WEBHOOK_URL` | HTTP endpoint for robot alert webhooks | (disabled) |
| `NOTIFY_EVENTS` | Which events trigger the webhook | `offline,error,task_failed` |
| `ROBOT_OFFLINE_THRESHOLD` | Seconds before a silent robot is flagged offline | `30` |

See [`.env.example`](../.env.example) for the full list.
