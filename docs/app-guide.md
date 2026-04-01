# Mosoro Demo App — Complete User & Developer Guide

> **Version:** 1.0 (Demo)  
> **Last updated:** 2026-04

---

## Table of Contents

1. [What Is This App?](#1-what-is-this-app)
2. [How Data Flows (Architecture)](#2-how-data-flows-architecture)
3. [Getting Started](#3-getting-started)
4. [Screen-by-Screen Reference](#4-screen-by-screen-reference)
   - [Login](#41-login)
   - [Dashboard](#42-dashboard--fleet-overview)
   - [Robots List](#43-robots-list)
   - [Robot Detail](#44-robot-detail)
   - [Map View](#45-map-view)
   - [Tasks](#46-tasks--task-assignment)
   - [Events Feed](#47-events-feed)
   - [Extensions](#48-extensions)
5. [Adding Robots](#5-adding-robots)
6. [Removing Robots](#6-removing-robots)
7. [Task Assignment — How Actions Work](#7-task-assignment--how-actions-work)
8. [User Accounts & Roles](#8-user-accounts--roles)
9. [Audit Logging](#9-audit-logging)

---

## 1. What Is This App?

Mosoro is an open-source semantic interoperability gateway — the neutral communication bridge for multi-vendor robot fleets. It normalizes messages from different robot vendors into a common schema, so that robots from different manufacturers can work together without custom point-to-point integrations.

The dashboard in this demo is the **control plane** on top of that communications layer: monitor, command, and coordinate robots from different manufacturers (Locus, MiR, Fetch, Geekplus, Boston Dynamics Stretch, etc.) without needing to log into each vendor's separate system.

**Key capabilities in the current demo:**
- Real-time robot status (position, battery, task, health)
- 2D spatial map of all robot positions
- Task assignment (send commands to individual robots)
- Live event feed (all MQTT messages from the fleet)
- Extension marketplace (premium add-ons)

---

## 2. How Data Flows (Architecture)

```
Physical Robot
     │
     ▼
Robot Adapter          ← translates vendor API → Mosoro standard format
     │  (MQTT publish)
     ▼
Mosquitto MQTT Broker  ← message bus for all robot events
     │
     ▼
MQTTFleetSubscriber    ← background thread in the FastAPI server
     │                    maintains in-memory fleet state
     ▼
FastAPI (REST + WS)    ← /robots, /tasks, /events, WS /ws/fleet
     │
     ▼
React Frontend         ← useFleetWebSocket() opens WS on app load
     │                    receives initial_state + robot_update messages
     ▼
All Pages              ← fleetData passed as props from App.tsx
```

**The map, robot list, dashboard, and task form all read from the same `fleetData` object** — a single WebSocket connection shared across the entire app. There is no polling; updates are pushed in real time.

---

## 3. Getting Started

### Demo Mode (no real robots needed)

```bash
git clone https://github.com/mosoroio/mosoro-core.git
cd mosoro-core
make demo
# Open http://localhost:3000
# Default login: admin / admin
```

This starts 3 virtual robots (a Locus, a MiR, and a Fetch) that move around and publish simulated MQTT messages.

### Connect Real Robots

```bash
make setup
```

The interactive wizard will:
1. Ask which robot vendors you have
2. Install only the adapters you need
3. Prompt for each robot's IP address / API credentials
4. Generate `robots.yaml` and `.env` configuration files
5. Start all services

See [`robots.yaml.example`](../robots.yaml.example) for the configuration format.

---

## 4. Screen-by-Screen Reference

### 4.1 Login

**URL:** `/login`

A simple username/password form. On submit it calls `POST /auth/token` and stores the returned JWT in `localStorage`. All subsequent API calls and the WebSocket connection use this token.

**Current limitation:** There is only one hardcoded admin account in the demo. See [Section 8](#8-user-accounts--roles) for the multi-user gap.

---

### 4.2 Dashboard — Fleet Overview

**URL:** `/` (root)

The landing page after login. Shows summary cards and a breakdown of the fleet.

| Element | What it shows |
|---|---|
| **Total Robots** | Count of all robots the API knows about |
| **Online / Offline** | Robots that have sent a heartbeat recently vs. those that haven't |
| **By Vendor** | Breakdown of how many robots per manufacturer |
| **By Status** | Count of robots in each state (idle, moving, working, charging, error) |
| **Fleet table** | Sortable list of all robots with status badges |

Data refreshes automatically via WebSocket — no page reload needed.

---

### 4.3 Robots List

**URL:** `/robots`

A full sortable/filterable table of every robot in the fleet.

| Column | Description |
|---|---|
| Robot ID | Unique identifier (set by the adapter, usually the vendor's device ID) |
| Vendor | Manufacturer name |
| Status | Current operational state |
| Battery | Charge percentage (if reported by the robot) |
| Health | Health string from the robot (e.g., "ok", "warning") |
| Last Updated | Timestamp of the last MQTT message from this robot |

**Interactions:**
- Click any row → navigates to the Robot Detail page
- Sort by any column header
- Filter by status using the dropdown
- Search by robot ID using the text input

**⚠️ Known Gap:** There is no "Add Robot" button on this page. Adding a robot requires editing `robots.yaml` and restarting the adapter service. A link to the Extensions page or a setup wizard should be added here. See [Section 10](#10-v1-feature-gaps--recommendations).

---

### 4.4 Robot Detail

**URL:** `/robots/:id`

Detailed view for a single robot.

| Section | Content |
|---|---|
| **Header** | Robot ID, vendor badge, online/offline indicator |
| **Status card** | Current status, battery %, health string |
| **Position card** | X, Y coordinates and heading angle (theta) |
| **Current Task** | Task ID, task type, progress % |
| **Recent Events** | Last N MQTT events from this specific robot |

Navigated to by clicking a robot in the list, map, or dashboard.

---

### 4.5 Map View

**URL:** `/map`

An SVG-based 2D coordinate map of all robots with known positions.

**What it shows:**
- Each robot as a colored circle at its `(x, y)` position
- A heading line showing which direction the robot is facing (`theta`)
- An animated pulse ring for online robots
- A fading trail of the last 8 positions (movement history)
- Robot ID label below each marker

**Controls:**

| Control | How |
|---|---|
| **Zoom in/out** | Mouse wheel, or pinch on mobile |
| **Pan** | Click and drag |
| **Reset View** | "Reset View" button — returns to default zoom/pan |
| **Color by Vendor** | Dropdown — colors each robot by its manufacturer |
| **Color by Status** | Dropdown — colors each robot by its current state |

**Hover a robot:** Shows a tooltip with ID, vendor, status, battery, current task, and coordinates.

**Click a robot:** Navigates to that robot's detail page.

**How positions work:** The map has **no fixed floor plan or coordinate origin**. It auto-scales to fit all robot positions. The coordinate system is whatever the robots report — typically meters from their charging dock or a map origin defined in the robot's own navigation system. If you want a warehouse floor plan as a background image, that is a V1 gap (see [Section 10](#10-v1-feature-gaps--recommendations)).

**Robots not appearing on the map:** A robot only appears if its adapter is publishing a `position` field in its MQTT status messages. Some adapters may not report position if the robot's API doesn't expose it.

---

### 4.6 Tasks — Task Assignment

**URL:** `/tasks`

A form to send a command to a robot.

**Fields:**

| Field | Required | Description |
|---|---|---|
| **Robot** | Yes | Dropdown of currently **online** robots only |
| **Action** | Yes | The command to send (see below) |
| **Position X/Y/Z** | No | Target coordinates for movement commands |
| **Parameters** | No | Free-form JSON for action-specific options |

**How the Action dropdown is populated:**

The actions are a **hardcoded list** in [`src/types/robot.ts`](../frontend/src/types/robot.ts) — they are **not** fetched from the API or the robot:

```typescript
export const TASK_ACTIONS = ["move_to", "pick", "dock", "pause", "resume"];
```

| Action | What it does |
|---|---|
| `move_to` | Navigate to the given X/Y/Z position |
| `pick` | Pick up an item at the given position |
| `dock` | Return to charging dock |
| `pause` | Pause current task |
| `resume` | Resume paused task |

**⚠️ Important:** These actions are generic. Whether a specific robot actually supports an action depends on its adapter. If the adapter doesn't implement the action, the robot will ignore it or return an error. The API passes the action through to the adapter without validation.

**How task submission works:**
1. Form calls `POST /tasks` with `{ robot_id, action, position?, parameters? }`
2. The API looks up the robot's adapter and forwards the command via MQTT
3. The adapter translates it to the robot's native API call
4. The response includes a `task_id`, `success` boolean, and a message
5. Feedback is shown for 5 seconds, then cleared

**⚠️ Known Gap:** Actions are not robot-aware. A `pick` command sent to a MiR (which can't pick) will fail silently. V1 should filter available actions based on the selected robot's vendor/capabilities.

---

### 4.7 Events Feed

**URL:** `/events`

A live stream of all MQTT messages received from the fleet.

| Column | Description |
|---|---|
| Time | When the event was received by the API |
| Robot ID | Which robot sent it |
| Vendor | Robot manufacturer |
| Topic | The MQTT topic (e.g., `mosoro/robots/robot-1/status`) |
| Payload | The raw JSON payload (expandable) |

Events are stored in memory in the API (last 500 events). They are **not persisted to a database** in the current demo. See [Section 9](#9-audit-logging) for the audit gap.

---

### 4.8 Extensions

**URL:** `/extensions`

A marketplace-style catalog of premium add-ons.

| Extension | Category | Description |
|---|---|---|
| **Black Box** | Compliance | Records all robot actions for incident review |
| **Safety Pro** | Security | Advanced threat detection and access control |
| **Facility Memory** | AI | AI-powered coordination and route optimization |

Extensions are loaded from a local [`catalog.json`](../frontend/src/data/catalog.json) file. "Install" buttons are UI-only in the demo — they do not actually install anything. Real installation requires the corresponding Docker service to be running (see `docker-compose.yml`).

---

## 5. Adding Robots

Robots are **not added through the UI** in the current version. To add a robot:

### Step 1 — Install the adapter

```bash
# Example: add a MiR robot
pip install mosoro-adapter-mir
```

Or use `make setup` to run the interactive wizard.

### Step 2 — Configure the robot in `robots.yaml`

```yaml
robots:
  - id: mir-001
    vendor: mir
    host: 192.168.1.100
    api_key: your-mir-api-key
```

See [`robots.yaml.example`](../robots.yaml.example) for all options.

### Step 3 — Restart the agent service

```bash
docker compose restart agent
```

The agent will connect to the robot, start polling its status, and publish MQTT messages. The robot will appear in the dashboard within a few seconds.

**⚠️ V1 Gap:** There is no in-app UI to add robots. This is a significant onboarding friction point. See [Section 10](#10-v1-feature-gaps--recommendations).

---

## 6. Removing Robots

Robots are also **not removed through the UI**. To remove a robot:

1. Delete or comment out its entry in `robots.yaml`
2. Restart the agent: `docker compose restart agent`

The robot will stop publishing MQTT messages. After the API's offline timeout (configurable, default ~30 seconds), the robot will be marked as offline. It will **remain in the list** as offline until the API is restarted, because the current in-memory state is never garbage-collected.

**⚠️ V1 Gap:** There is no way to permanently remove a robot from the UI or via the API. The offline robot will persist in the list until the API restarts.

---

## 7. Task Assignment — How Actions Work

The full flow when you submit a task:

```
Browser form
    │  POST /tasks { robot_id, action, position, parameters }
    ▼
FastAPI /tasks endpoint
    │  looks up robot in mqtt_subscriber._robots
    │  publishes to MQTT topic: mosoro/robots/{robot_id}/commands
    ▼
Mosquitto MQTT broker
    │
    ▼
Robot Adapter (running as a separate process)
    │  subscribes to mosoro/robots/{robot_id}/commands
    │  translates action → vendor-specific API call
    ▼
Physical Robot
    │  executes the command
    │  publishes status update back to MQTT
    ▼
Dashboard updates in real time
```

**Why are actions hardcoded?**

The 5 actions (`move_to`, `pick`, `dock`, `pause`, `resume`) are the current Mosoro standard action vocabulary. Every adapter is expected to implement these. Custom actions can be passed via the `parameters` JSON field.

**Future:** Actions should be dynamically fetched per robot based on what its adapter declares it supports.

---

## 8. User Accounts & Roles

**Current state:** The demo has a single hardcoded admin account. There is no multi-user support, no role-based access control, and no user management UI.

**What V1 needs:**

| Role | Permissions |
|---|---|
| **Admin** | Full access — add/remove robots, manage users, view all data |
| **Facility Manager** | View all robots, assign tasks, view events |
| **Operator / Employee** | View robots, assign tasks to their assigned zone |
| **Maintenance** | View robot health/errors, cannot assign tasks |
| **Read-only / Viewer** | Dashboard and map only, no task assignment |

**Recommended implementation:**
- Add a `users` table to the database with `role` field
- Protect API endpoints with role checks (FastAPI dependency injection)
- Add a `/admin/users` page in the frontend for user management
- Use JWT claims to carry the user's role

---

## 9. Audit Logging

**Current state:** There is **no audit logging**. Events are stored in memory (last 500) and lost on API restart. Task assignments are not logged anywhere.

**What V1 needs for compliance:**

| Event type | Should be logged |
|---|---|
| User login / logout | ✅ |
| Task assigned (who, to which robot, what action) | ✅ |
| Robot added / removed | ✅ |
| Robot error events | ✅ |
| Extension installed / uninstalled | ✅ |
| Configuration changes | ✅ |

**Recommended implementation:**
- Persist events to a database (PostgreSQL or Supabase)
- Add `user_id` to task assignment requests so you know who sent each command
- The **Black Box** premium extension is designed for this — it records all robot actions for incident review and compliance

