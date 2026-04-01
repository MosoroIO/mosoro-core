# Mosoro

[![CI](https://github.com/mosoroio/mosoro-core/actions/workflows/ci.yml/badge.svg)](https://github.com/mosoroio/mosoro-core/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/pypi/pyversions/mosoro-core)](https://pypi.org/project/mosoro-core/)

The open-source communication bridge for multi-vendor robot fleets.

## Try It Now (no robots needed)

```bash
git clone https://github.com/mosoroio/mosoro-core.git
cd mosoro-core
make demo
# Open http://localhost:3000 — 3 virtual robots on the dashboard
```

## Connect Real Robots

```bash
make setup    # Interactive wizard — choose adapters, enter robot IPs
```

The setup wizard shows available robot adapters, installs only what you need,
and generates your configuration automatically.

## Supported Robots

| Robot | Adapter | Status |
|-------|---------|--------|
| Locus Robotics AMR | `mosoro-adapter-locus` | ✅ Free |
| MiR Mobile Industrial | `mosoro-adapter-mir` | ✅ Free |
| Fetch Robotics (Zebra) | `mosoro-adapter-fetch` | ✅ Free |
| Geekplus / Seer AMR | `mosoro-adapter-geekplus` | ✅ Free |
| Boston Dynamics Stretch | `mosoro-adapter-stretch` | ✅ Free |

Don't see your robot? [Build an adapter](docs/adapter-guide.md) or [contact us](https://mosoro.io/services).

## How It Works

```
Robot → Adapter → MQTT → Gateway → API → Dashboard
```

Each robot vendor gets a thin adapter that translates its native API
into Mosoro's common message format. The gateway manages the fleet.
The dashboard shows everything in real-time.

## Premium Extensions

Browse premium features in the dashboard's Extensions page:

- **Black Box** — Incident recording & compliance
- **Safety Pro** — Advanced security & threat detection
- **Facility Memory** — AI-powered coordination

## Documentation

- [Dashboard User Guide](docs/user-guide.md)
- [Architecture Overview](docs/architecture.md)
- [Adapter Development Guide](docs/adapter-guide.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## License

Copyright 2026 Mosoro Inc.

Apache License 2.0 — see [LICENSE](LICENSE).
