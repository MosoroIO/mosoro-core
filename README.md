[![CI](https://github.com/mosoro/mosoro-core/actions/workflows/ci.yml/badge.svg)](https://github.com/mosoro/mosoro-core/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/mosoro-core.svg)](https://badge.fury.io/py/mosoro-core)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# Mosoro

**The neutral bridge for multi-vendor warehouse robot fleets.**

Mosoro is a lightweight, open-core middleware platform that enables seamless interoperability between mixed-vendor robot fleets (Locus, Boston Dynamics Stretch, Geekplus/Seer, MiR, UR, and more). It provides deterministic protocol translation, real-time routing, and a unified API/dashboard — without the complexity of a full HFMS platform.

> Mosoro core is open source under [Apache License 2.0](LICENSE). Premium features and hosted SaaS remain commercial.

---

## Why Mosoro?

Warehouses today run 3–5 different robot vendors that cannot talk to each other. Integration costs $$$$$ per vendor and takes weeks. Mosoro solves this with:

- **Plug-and-play adapters** — drop in a YAML config and a thin Python adapter per robot
- **Neutral MQTT backbone** — all robots speak the same `MosoroMessage` schema
- **Zero-trust security** — mTLS, JWT, TLS 1.3, and least-privilege ACLs from day one
- **Deployment in days, not months** — Docker Compose for pilots, Kubernetes for production
- **Open-core flywheel** — Apache 2.0 core drives community adapter contributions

---

## Quick Install

```bash
# Install core library
pip install mosoro-core

# Install with all optional dependencies
pip install mosoro-core[all]

# Install specific extras
pip install mosoro-core[api]      # FastAPI + uvicorn
pip install mosoro-core[agents]   # Agent framework
pip install mosoro-core[security] # mTLS + JWT
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Mosoro Stack                         │
├──────────────┬──────────────────────────┬───────────────────┤
│  Edge Agents │    Central Gateway       │   Unified API     │
│  (per robot) │  (MQTT + Rules Engine)   │  (REST + WS)      │
├──────────────┼──────────────────────────┼───────────────────┤
│ locus_adapter│                          │  /robots          │
│ stretch_adapt│  mosoro/v1/agents/+/     │  /robots/{id}     │
│ geekplus_adpt│  status, events,         │  /tasks           │
│ [your_adapter│  commands, traffic       │  /ws/fleet        │
└──────────────┴──────────────────────────┴───────────────────┘
                         ↕ mTLS / TLS 1.3
              ┌──────────────────────────────┐
              │   Eclipse Mosquitto 2.x      │
              │   Port 8883 (TLS) + ACLs     │
              └──────────────────────────────┘
```

**MQTT Topic Hierarchy:**
```
mosoro/v1/agents/{robot_id}/birth       ← connection management
mosoro/v1/agents/{robot_id}/lwt         ← last will & testament
mosoro/v1/agents/{robot_id}/status      ← periodic status (QoS 1)
mosoro/v1/agents/{robot_id}/events      ← task complete, errors, alerts
mosoro/v1/agents/{robot_id}/commands    ← gateway → agent commands
mosoro/v1/traffic/yield                 ← broadcast traffic control
mosoro/v1/traffic/update                ← broadcast traffic updates
mosoro/v1/admin/rules                   ← admin-only rules management
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Messaging | MQTT (Eclipse Mosquitto 2.x) + paho-mqtt |
| Schema & Validation | Pydantic v2 |
| API | FastAPI + WebSocket |
| Frontend | React + Vite |
| Containerization | Docker + Docker Compose (dev/pilot), Kubernetes (production) |
| Database | SQLite (OSS) / PostgreSQL (paid tiers) |
| Security | mTLS, JWT, TLS 1.3, rate limiting, SBOM per release |
| License | Apache 2.0 (core) |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- TLS certificates (generate with `security/scripts/generate_certs.py`)

### 1. Generate TLS Certificates

```bash
python security/scripts/generate_certs.py
```

This creates `certs/ca.crt`, `certs/server.crt`, and `certs/server.key`.

### 2. Create MQTT Password File

```bash
mosquitto_passwd -c docker/mosquitto/passwordfile gateway
mosquitto_passwd -b docker/mosquitto/passwordfile api <strong-password>
```

### 3. Configure Your Robots

Copy and edit the agent config files in `agents/config/`:

```bash
cp agents/config/locus.yaml agents/config/my-locus-001.yaml
# Edit: robot_id, api_base_url, api_key
```

### 4. Run the Full Stack

**Development (no TLS):**
```bash
docker compose -f docker/docker-compose.yml up --build
```

**Production (TLS + mTLS):**
```bash
docker compose -f docker/docker-compose.prod.yml up --build
```

### 5. Access the Dashboard

- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Fleet WebSocket:** ws://localhost:8000/ws/fleet
- **Dashboard:** http://localhost:3000

---

## Adding a New Robot Adapter

1. Create `agents/adapters/myrobot_adapter.py`
2. Subclass `BaseMosoroAdapter` and implement two methods:
   - `_fetch_robot_status()` → returns dict compatible with `MosoroPayload`
   - `send_command(command)` → sends command to the physical robot
3. Create `agents/config/myrobot.yaml` with `vendor: "myrobot"`
4. Add the agent service to `docker-compose.yml`

No changes to `agent.py` needed — auto-discovery handles the rest.

```python
# agents/adapters/myrobot_adapter.py
from agents.adapters.base_adapter import BaseMosoroAdapter

class MyrobotAdapter(BaseMosoroAdapter):
    vendor_name = "myrobot"

    async def _fetch_robot_status(self) -> dict:
        # Call your robot's API here
        return {"position": {"x": 0.0, "y": 0.0}, "battery": 100.0, "status": "idle"}

    async def send_command(self, command: dict) -> bool:
        # Send command to your robot here
        return True
```

---

## Plugin System

Mosoro Core supports extensions via Python entry points. Premium modules and community extensions can register:

- **API Routers** — Additional REST endpoints mounted under `/plugins/{name}/`
- **MQTT Topics** — Additional topic subscriptions
- **Gateway Hooks** — Event handlers for message processing

### Creating a Plugin

1. Create a Python package with a plugin factory function:

```python
# my_plugin/__init__.py
from mosoro_core.plugin_types import MosoroPlugin
from my_plugin.router import router

def plugin() -> MosoroPlugin:
    return MosoroPlugin(
        name="my-plugin",
        version="1.0.0",
        description="My custom Mosoro plugin",
        api_router=router,
    )
```

2. Register it in your `pyproject.toml`:

```toml
[project.entry-points."mosoro.plugins"]
my_plugin = "my_plugin:plugin"
```

3. Install your package and restart Mosoro — the plugin is auto-discovered.

See [docs/architecture.md](docs/architecture.md) for the full plugin API reference.

---

## Repository Structure

```
mosoro/
├── mosoro_core/          # Shared models, topic constants, utilities
├── agents/               # Edge agents
│   ├── core/             # agent.py (auto-discovery), config.py
│   ├── adapters/         # locus, stretch, geekplus, mir, fetch adapters
│   ├── config/           # Per-robot YAML configs
│   ├── Dockerfile.agent
│   └── requirements.txt
├── gateway/              # Central gateway + rules engine
│   ├── gateway.py
│   ├── state.py          # In-memory state store with TTL
│   ├── rules.yaml.example
│   └── Dockerfile.gateway
├── api/                  # Unified REST API + WebSocket backend
│   ├── main.py           # FastAPI app
│   ├── models.py         # Pydantic schemas
│   ├── mqtt_subscriber.py
│   └── Dockerfile.api
├── frontend/             # React + Vite dashboard
│   └── src/
├── security/             # mTLS, JWT, cert generation
│   ├── mqtt_tls.py       # MQTT client factory with mTLS
│   ├── auth.py           # FastAPI JWT middleware
│   └── scripts/generate_certs.py
├── certs/                # TLS certificates (not committed to git)
├── docker/               # Docker Compose files + Mosquitto config
│   ├── docker-compose.prod.yml
│   └── mosquitto/
│       ├── mosquitto.conf
│       └── aclfile
├── tests/                # Unit + integration tests
├── docs/                 # Blueprint, roadmap, license docs
├── plans/                # Architecture plans and audit reports
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
```

---

## Documentation

- [Architecture Overview](docs/architecture.md) — System design, MQTT topics, plugin system
- [Contributing Guide](CONTRIBUTING.md) — How to contribute to Mosoro
- [Security Policy](SECURITY.md) — Vulnerability reporting and security best practices
- [License](LICENSE) — Apache License 2.0

---

## Phase 1 MVP Adapters

| Priority | Adapter | Status |
|---|---|---|
| 1 | Locus Robotics AMR | ✅ Implemented |
| 2 | Boston Dynamics Stretch | ✅ Implemented |
| 3 | Geekplus / Seer AMR | ✅ Implemented |
| 4 | MiR (Mobile Industrial Robots) | ✅ Implemented |
| 5 | Fetch Robotics (Zebra) | ✅ Implemented |

---

## Security

Mosoro is designed for zero-trust OT/warehouse environments:

- **mTLS** — All agent-to-gateway MQTT communication uses mutual TLS (both sides present certificates)
- **TLS 1.3** — Enforced on MQTT port 8883
- **JWT** — All REST API calls require a valid JWT bearer token
- **Least-privilege ACLs** — Each robot can only publish to its own `mosoro/v1/agents/{robot_id}/#` topics
- **Non-root containers** — All Docker containers run as non-root user `mosoro`
- **IEC 62443 alignment** — Documentation available in `docs/`

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

By contributing, you agree that your contribution is licensed under the Apache License 2.0 and that you grant Mosoro Inc. a perpetual, worldwide, non-exclusive, royalty-free license to use, reproduce, and distribute your contribution.

**Priority areas for community contributions:**
- New robot adapters (see adapter template in `agents/adapters/base_adapter.py`)
- Integration tests with simulated robots
- Dashboard improvements
- Documentation and translations

For security-related issues, please contact security@mosoro.com instead of opening a public issue.

---

## License

Copyright 2026 Mosoro Inc.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.

Mosoro core is open source under Apache License 2.0. Premium features and hosted SaaS remain commercial.

---

## Contact

- **Website:** https://mosoro.com
- **GitHub:** https://github.com/mosoro
- **Founder:** info@mosoro.com
