<div align="center">

# SAMM

### SecuryTik Active MikroTik Manager

**Full-stack ISP management platform for MikroTik PPPoE & Hotspot networks**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white&style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi&logoColor=white&style=flat-square)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?logo=postgresql&logoColor=white&style=flat-square)](https://postgresql.org)
[![FreeRADIUS](https://img.shields.io/badge/FreeRADIUS-3-CC0000?style=flat-square&logoColor=white)](https://freeradius.org)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%20%7C%20Debian-E95420?logo=ubuntu&logoColor=white&style=flat-square)](https://ubuntu.com)

[**securytik.com**](https://securytik.com) &nbsp;·&nbsp; [Report a Bug](https://github.com/your-org/samm/issues) &nbsp;·&nbsp; [Request a Feature](https://github.com/your-org/samm/issues)

</div>

---

## Overview

SAMM is an open-source ISP management platform built on top of FreeRADIUS and PostgreSQL. It handles subscriber authentication, real-time usage enforcement, and billing for MikroTik-based PPPoE and Hotspot deployments — with a polished web portal for both administrators and end customers.

The stack is designed to keep logic close to the database: byte accumulation, limit evaluation, and CoA enqueueing all happen inside PostgreSQL functions called directly by FreeRADIUS `unlang` on every Interim-Update, with no Python round-trip on the critical path.

```
MikroTik(s) ──Auth/Acct──► FreeRADIUS ──unlang+rlm_sql──► PostgreSQL
                ▲                                               │
                │                                               ▼
                └──── CoA / Disconnect ◄──── samm-radius · samm-worker · samm-api
```

---

## Features

<table>
<tr>
<td valign="top" width="50%">

**🔐 AAA Core**
- FreeRADIUS 3 + PostgreSQL, PAP/CHAP
- PPPoE and Hotspot support
- Hybrid CoA: CoA-Update → auto-fallback to Disconnect-Request
- Dynamic NAS registration — no FR restart on add/remove
- Per-user static IP override

**📊 Plans & Limits**
- Speed (download/upload Mbps) + optional RADIUS Framed-Pool
- 4 independent limits per plan: `expiration`, `quota`, `uptime`, `daily`
- Each limit can throttle, switch plan, or disconnect on exhaust
- Speed windows: scheduled boosts with midnight-crossing support
- Non-resettable billing counters separate from resettable limit state

**💰 Financial Accounting**
- Double-entry accounting engine
- Invoices, expenses, resellers, assets, depreciation
- Automatic overdue-invoice detection

</td>
<td valign="top" width="50%">

**🖥️ Admin Portal**
- Customer and plan CRUD
- Live MikroTik device inventory (ping, RouterOS version, interfaces)
- Firewall backup and scheduled revert
- WiFi / cAPsMAN management
- Hotspot voucher card generation & printing
- Customer support ticket queue
- Role-based permissions (superadmin / manager / viewer, per page block)

**👤 Customer Portal**
- Self-service: usage, plan info, invoices, support tickets

**🌍 Multilingual & Themeable**
- 6 built-in languages: English, Arabic (RTL), Turkish, French, Spanish, German
- Live translation editor at `/admin/translations` — no restart needed
- 11 visual themes, preference saved per user account

</td>
</tr>
</table>

---

## Requirements

| Requirement | Notes |
|---|---|
| Ubuntu 22.04 / 24.04 or Debian 12 | Other Debian-based distros likely work |
| `nginx` | Proxies port 80 → 8000; **not** installed by `install.sh` |
| Root / sudo access | Required for apt, systemd, and FreeRADIUS config |
| SAMM source at `/opt/samm` | Via git clone or file copy |

The following are installed automatically by `install.sh`:
`freeradius` `freeradius-postgresql` `freeradius-utils` `postgresql` `postgresql-client` `python3` `python3-venv` `python3-pip` `libpq-dev` `iputils-ping`

---

## Installation

### Step 1 — Get the source

```bash
git clone https://github.com/your-org/samm.git /opt/samm
```

### Step 2 — Run the installer

```bash
sudo bash /opt/samm/install.sh
```

The installer is **fully idempotent** — safe to re-run for upgrades. It:

- Installs system packages via `apt`
- Creates the `samm` system user and directories
- Rsyncs source into `/opt/samm` (skips `venv/`, `.git`, `__pycache__`)
- Builds the Python venv and installs `requirements.txt`
- Compiles i18n catalogs and runs glossary lint
- Generates `/etc/samm/samm.yaml` with a **random DB password** (first run only — re-runs extract the existing password so the database is never re-keyed)
- Generates `/etc/samm/api.env` with random cookie signing secrets (first run only)
- Generates `/etc/samm/secret.key` (Fernet key for MikroTik API passwords)
- Creates the `samm` PostgreSQL role + database, applies all SQL migrations
- Deploys and validates FreeRADIUS config (`freeradius -CX`)
- Installs and starts systemd units: `freeradius`, `samm-radius`, `samm-worker`, `samm-api`

When done, credentials are printed:

```
============================================================
  Default admin login : admin / admin  <- CHANGE AFTER FIRST LOGIN
  DB user   : samm
  DB pass   : <auto-generated>
  Secrets   : /etc/samm/api.env
  To enable email OTP, set SMTP_* in /etc/samm/api.env
============================================================
```

### Step 3 — Configure nginx

```nginx
server {
    listen 80;
    server_name samm.example.com;

    client_max_body_size 20M;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

```bash
nginx -t && systemctl reload nginx
```

### Step 4 — First login

Navigate to `http://your-server/admin/login`

- Username: `admin`
- Password: `admin`
- **Change your password immediately** via the profile page

### Step 5 — Add your first router

Go to **Admin → NAS / Routers → Add** and fill in the router's IP, RADIUS shared secret, and (optionally) MikroTik API credentials for live device sync. No FreeRADIUS restart needed — NAS records are resolved dynamically from the database.

---

## Configuration

### `/etc/samm/samm.yaml`

Shared by all three Python services. Contains the canonical DB DSN — never duplicate it elsewhere.

```yaml
db:
  dsn: "postgresql://samm:<password>@127.0.0.1:5432/samm"
  min_size: 2
  max_size: 10

log:
  level: INFO   # DEBUG / INFO / WARNING / ERROR

secret_key_file: "/etc/samm/secret.key"
```

### `/etc/samm/api.env`

Loaded by `samm-api` via systemd `EnvironmentFile=`. **Preserve this file across upgrades** — rotating the cookie secrets invalidates all active sessions. `samm-api` refuses to start if `ADMIN_SECRET` or `CUSTOMER_SECRET` is missing or uses the placeholder default.

```bash
DISPLAY_TIMEZONE=UTC          # portal display timezone (e.g. Asia/Beirut)
ADMIN_SECRET=<random>         # admin session cookie key — keep stable
CUSTOMER_SECRET=<random>      # customer session cookie key — keep stable

# Email (OTP password recovery) — leave blank to disable
SMTP_HOST=
SMTP_PORT=465
SMTP_USE_SSL=1
SMTP_USERNAME=
SMTP_FROM=SAMM <noreply@example.com>
SMTP_PASSWORD=
```

### Live tunables — `samm.settings` table

Updated at runtime with no restart required:

```sql
UPDATE samm.settings SET value = '15' WHERE key = 'samm_radius_interval_seconds';
```

| Key | Default | Description |
|---|---|---|
| `samm_radius_interval_seconds` | `30` | samm-radius loop cadence |
| `samm_worker_interval` | `60` | Router ping + API sync cadence |
| `acct_interim_interval_seconds` | `60` | Acct-Interim-Interval pushed to routers |
| `daily_reset_time` | `00:00` | Time of daily counter rollover |
| `server_timezone` | `UTC` | Timezone for windows + daily reset |
| `coa_default_port` | `3799` | Default CoA UDP port |
| `coa_retry_max` | `3` | CoA retries before Disconnect-Request fallback |

---

## Service Management

```bash
# Status overview
systemctl status freeradius samm-api samm-radius samm-worker

# Restart all
systemctl restart freeradius samm-api samm-radius samm-worker

# Live logs
journalctl -u samm-api     -f
journalctl -u samm-radius  -f
journalctl -u samm-worker  -f

# Validate FreeRADIUS config after any change under freeradius/
freeradius -CX

# Run a daemon in the foreground for debugging
sudo -u samm SAMM_CONFIG=/etc/samm/samm.yaml /opt/samm/venv/bin/python -m samm_radius.main
sudo -u samm SAMM_CONFIG=/etc/samm/samm.yaml /opt/samm/venv/bin/python -m samm_worker.main

# Port 8000 stuck after a crash
kill -9 $(lsof -ti:8000) && systemctl restart samm-api
```

---

## Admin CLI

The CLI inserts rows into `samm.audit_log`. `samm-radius` applies them on its next tick (≤ `samm_radius_interval_seconds`) and sends a live CoA refresh if the subscriber is online.

```bash
CLI="sudo -u samm /opt/samm/venv/bin/python -m samm_radius.cli"

$CLI reset-quota       alice      # reset quota counter
$CLI reset-daily       alice      # reset daily counter
$CLI reset-uptime      alice      # reset uptime counter
$CLI reset-expiration  alice      # reset expiration counter

$CLI change-plan alice home-50M   # switch plan (takes effect within one tick)

$CLI encrypt-pw                   # encrypt a MikroTik API password for the DB
```

---

## Upgrading

```bash
git -C /opt/samm pull
sudo bash /opt/samm/install.sh
```

The installer re-syncs the source, upgrades the venv, re-applies all SQL migrations (every file is idempotent), reloads FreeRADIUS config, and restarts the services. `/etc/samm/samm.yaml`, `/etc/samm/api.env`, and `/etc/samm/secret.key` are **never overwritten** on upgrades.

---

## RADIUS Smoke Test

```bash
# 1. Authenticate
radtest alice alicepw 127.0.0.1 0 testing123

# 2. Acct-Start
echo 'Acct-Status-Type = Start
Acct-Session-Id = "s-1"
User-Name = "alice"
NAS-IP-Address = 127.0.0.1
Framed-IP-Address = 10.0.0.55' | radclient -x 127.0.0.1:1813 acct testing123

# 3. Interim-Update (triggers limit evaluation inside PostgreSQL)
echo 'Acct-Status-Type = Interim-Update
Acct-Session-Id = "s-1"
User-Name = "alice"
NAS-IP-Address = 127.0.0.1
Acct-Input-Octets = 800000
Acct-Output-Octets = 400000
Acct-Session-Time = 30' | radclient -x 127.0.0.1:1813 acct testing123

# 4. Inspect DB state
psql -h 127.0.0.1 -U samm -d samm -c "TABLE samm.user_limit_state;"
psql -h 127.0.0.1 -U samm -d samm -c "TABLE samm.coa_outbox;"
psql -h 127.0.0.1 -U samm -d samm -c "TABLE samm.user_usage_daily;"
```

---

## Notes

- **Cleartext passwords** are required for PAP/CHAP. EAP is explicitly disabled by the installer.
- **CoA timing**: time-driven events (expiration, speed windows, daily reset) surface within `samm_radius_interval_seconds` (default 30 s). Lower this in `samm.settings` for tighter enforcement.
- **Remote PostgreSQL**: the installer assumes a local PG instance. For a remote DB, update `pg_hba.conf` on the DB server and set the DSN in `/etc/samm/samm.yaml` manually.
- **Legacy migration**: `sql/0006..0013` and `sql/legacy_to_samm.sql` are for migrating from a pre-SAMM `public.*` schema only — do not apply on a fresh install.

---

<div align="center">

Built by [SecuryTik](https://securytik.com)

</div>
