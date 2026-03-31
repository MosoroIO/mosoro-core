# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Mosoro Core, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities.
2. Email **security@mosoro.io** with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment** within 48 hours of your report
- **Assessment** within 5 business days
- **Fix timeline** communicated within 10 business days
- **Credit** in the security advisory (unless you prefer anonymity)

### Scope

The following are in scope for security reports:

- Authentication and authorization bypasses
- MQTT message injection or spoofing
- TLS/mTLS configuration weaknesses
- API endpoint vulnerabilities
- Dependency vulnerabilities with known exploits
- Certificate handling issues

### Out of Scope

- Denial of service attacks against development/test configurations
- Social engineering
- Issues in dependencies without a known exploit
- Issues requiring physical access to the deployment

## Demo Mode vs. Production Security

Mosoro Core ships with a `make demo` command for zero-configuration local evaluation. **Demo mode uses intentionally permissive defaults** that are unsuitable for production. The table below documents the differences:

| Setting | Demo Mode (`make demo`) | Production |
|---------|------------------------|------------|
| MQTT authentication | Anonymous — no credentials required | Password file + per-user ACLs |
| MQTT encryption | Plain TCP port 1883 | mTLS only — TLS 1.3, port 8883 |
| MQTT ACL | `mosoro/v1/#` open to all containers | Per-user topic restrictions |
| API admin password | `changeme-dev` (hardcoded default) | Set via `MOSORO_ADMIN_PASSWORD` env var |
| JWT secret | Known default (`dev-secret-...`) | Unique 64-char random value |
| Data source | Virtual fleet simulator (no real robots) | Real robot adapters |

**The demo MQTT broker is accessible only within the Docker bridge network** (`mosoro-net`). Port 1883 is mapped to localhost by default — if you run `make demo` on a shared or networked machine, restrict the port binding or use a firewall rule.

Demo mode weaknesses are **not security vulnerabilities** — they are documented, intentional trade-offs for ease of evaluation. Please do not report demo-mode defaults as vulnerabilities.

## Security Best Practices

When deploying Mosoro Core in production:

1. **Always use mTLS** — Generate unique certificates for each agent and component
2. **Enable JWT authentication** — Do not run the API without authentication in production
3. **Use ACLs** — Configure Mosquitto ACL to restrict topic access per agent
4. **Set strong secrets** — Use a unique, random `MOSORO_JWT_SECRET` and `MOSORO_ADMIN_PASSWORD`
5. **Rotate certificates** — Implement a certificate rotation schedule
6. **Monitor logs** — Watch for authentication failures and unusual MQTT patterns
7. **Keep updated** — Apply security patches promptly

## Disclosure Policy

We follow a coordinated disclosure process:

1. Reporter submits vulnerability privately
2. We confirm and assess the issue
3. We develop and test a fix
4. We release the fix and publish a security advisory
5. Reporter is credited (if desired)

We aim to resolve critical vulnerabilities within 30 days of confirmed report.
