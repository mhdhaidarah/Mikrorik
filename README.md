<div align="center">

<img src="app/admin/static/s-box-logo.svg" width="96" alt="SAMM logo" />

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

SAMM is an open-source ISP management platform built on FreeRADIUS and PostgreSQL. It handles subscriber authentication, real-time usage enforcement, and billing for MikroTik PPPoE and Hotspot deployments — with a polished web portal for administrators and customers.

The stack is designed to keep logic close to the database: byte accumulation, limit evaluation, and CoA enqueueing all run inside PostgreSQL functions called directly by FreeRADIUS `unlang` on every Interim-Update — no Python round-trip on the hot path.

```
MikroTik(s) ──Auth/Acct──► FreeRADIUS ──unlang+rlm_sql──► PostgreSQL
                ▲                                               │
                │                                               ▼
                └──── CoA / Disconnect ◄──── samm-radius · samm-worker · samm-api
                                                                │
                                                          nginx ◄─► cloudflared ──► Internet
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
- Dynamic NAS registration — no FreeRADIUS restart on add/remove
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
- Customer and plan management
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

## Installation

SAMM installs everything it needs — **one script, one server, online in minutes.**

### What the installer sets up automatically

| Component | Details |
|---|---|
| **FreeRADIUS 3** | Configured with PostgreSQL backend, dynamic NAS clients |
| **PostgreSQL** | Database + schema + all migrations applied automatically |
| **Python venv** | All Python dependencies from `requirements.txt` |
| **nginx** | Reverse-proxy on port 80 → 8000, SAMM vhost pre-configured |
| **samm-api** | FastAPI admin + customer portal (systemd unit) |
| **samm-radius** | CoA dispatcher + expiration/quota enforcement (systemd unit) |
| **samm-worker** | MikroTik API sync + ping monitor (systemd unit) |
| **cloudflared** | *(optional)* Cloudflare Zero Trust tunnel — paste your token |

All credentials (DB password, session signing keys) are **auto-generated** on first install.

### Prerequisites

- Ubuntu 22.04 / 24.04 or Debian 12
- Root / sudo access
- SAMM source code at `/opt/samm`

### Step 1 — Get the source

```bash
git clone https://github.com/your-org/samm.git /opt/samm
```

### Step 2 — Run the installer

```bash
sudo bash /opt/samm/install.sh
```

The installer is **idempotent** — safe to re-run for upgrades. Near the end it will prompt:

```
==> cloudflared

    Cloudflare Zero Trust — paste your connector token to expose SAMM
    online instantly without opening firewall ports.
    Get it from: https://one.dash.cloudflare.com → Networks → Tunnels
    (press Enter to skip — re-run install.sh later to add it)

    Token: █
```

Paste your connector token and press Enter. SAMM will be live on your Cloudflare domain immediately — no DNS changes, no open ports, no SSL configuration needed.

To skip and add it later, just press Enter. You can always add or update the tunnel by re-running:

```bash
CF_TOKEN='your-token' sudo bash /opt/samm/install.sh
```

### Step 3 — First login

When the installer finishes it prints a summary:

```
============================================================
  Admin portal  : http://localhost/admin/login
  Default login : admin / admin  <- CHANGE AFTER FIRST LOGIN
  DB user       : samm
  DB pass       : <auto-generated>
  Config files  : /etc/samm/samm.yaml  /etc/samm/api.env
  Cloudflare ZT : active — check tunnel status in the Cloudflare dashboard
  Email OTP     : set SMTP_* in /etc/samm/api.env to enable
============================================================
```

Open the admin portal via your Cloudflare tunnel URL or `http://server-ip/admin/login`.  
Log in with **admin / admin** and change your password immediately.

### Step 4 — Add your first router

Go to **Admin → NAS / Routers → Add**. Fill in the router's IP, RADIUS shared secret, and optionally MikroTik API credentials for live device sync. No FreeRADIUS restart needed — NAS records are resolved dynamically from the database.

### Step 5 — Point your MikroTik at SAMM

On the MikroTik, configure:
- **RADIUS server**: your server IP, port 1812/1813, the shared secret you entered in step 4
- **PPPoE / Hotspot**: set RADIUS authentication enabled, Interim-Update interval 60 s

That's it. SAMM handles everything else.

---

## Upgrading

```bash
git -C /opt/samm pull
sudo bash /opt/samm/install.sh
```

The installer re-syncs the source, upgrades the venv, re-applies all SQL migrations (every file is idempotent), reloads FreeRADIUS and nginx configs, and restarts all services. Your config files (`/etc/samm/samm.yaml`, `/etc/samm/api.env`, `/etc/samm/secret.key`) are **never overwritten** on re-runs.

---

## Configuration

### `/etc/samm/samm.yaml`

Shared by all Python services. Holds the canonical DB DSN — never duplicate it elsewhere.

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

Loaded by `samm-api` via systemd `EnvironmentFile=`. **Preserve this file across upgrades** — rotating the cookie secrets invalidates all active sessions.

```bash
DISPLAY_TIMEZONE=UTC          # portal display timezone (e.g. Asia/Beirut)
ADMIN_SECRET=<random>         # admin session cookie signing key — keep stable
CUSTOMER_SECRET=<random>      # customer session cookie signing key — keep stable

# Email (OTP password recovery) — leave blank to disable
SMTP_HOST=
SMTP_PORT=465
SMTP_USE_SSL=1
SMTP_USERNAME=
SMTP_FROM=SAMM <noreply@example.com>
SMTP_PASSWORD=
```

`samm-api` refuses to start if `ADMIN_SECRET` or `CUSTOMER_SECRET` is missing or still set to a placeholder value.

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
systemctl status freeradius nginx cloudflared samm-api samm-radius samm-worker

# Restart all SAMM services
systemctl restart samm-api samm-radius samm-worker

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

The CLI inserts rows into `samm.audit_log`. `samm-radius` applies them on its next tick and sends a live CoA refresh if the subscriber is currently online.

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

## Architecture

**FreeRADIUS** (`unlang` + `rlm_sql`) handles every Auth and Acct packet. On each Interim-Update it calls two PostgreSQL functions directly:

- `samm.apply_interim(acctuniqueid, in_bytes, out_bytes, session_secs)` — accumulates usage into `user_limit_state`, `user_usage_totals`, `user_usage_daily`
- `samm.evaluate_user_limits(user_id)` — first-exhausted-wins evaluation (`expiration → quota → daily → uptime`); inserts a `coa_outbox` row when a limit fires

**samm-radius** drains `samm.coa_outbox` via pyrad (CoA-Update → Disconnect-Request on NACK), runs the expiration sweep, daily reset, speed-window edge detection, and applies admin commands from `samm.audit_log`.

**samm-worker** pings every router and — for routers with API credentials — syncs identity, model, RouterOS version, and interface statistics from the MikroTik API.

**samm-api** is read/write for the web portals but **never sends CoAs directly**. Admin actions are written to `samm.audit_log` and applied by samm-radius within one tick.

---

## Plans and Limits

Plans define speed (download/upload Mbps), an optional RADIUS Framed-Pool, and up to four independent limit types:

| Limit | Tracks | On exhaust |
|---|---|---|
| `expiration` | Days since activation or assignment | `throttle`, `next_plan`, or `disconnect` |
| `quota` | Total bytes (configurable: both / download / upload) | same |
| `daily` | Bytes since last daily reset | same |
| `uptime` | Cumulative session seconds | same |

Each limit resets independently. `samm.user_limit_state` holds resettable counters; `samm.user_usage_totals` and `samm.user_usage_daily` hold permanent billing counters that are never zeroed.

**Speed windows** override the plan's base speed for specific days and clock ranges (highest-speed match wins). Throttled or exhausted users are excluded — the system never lifts speed while a limit is in force.

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
- **No SSL on the server** — SAMM runs on port 80 behind Cloudflare Zero Trust. TLS is terminated at the Cloudflare edge; the tunnel between cloudflared and the SAMM server is encrypted by the connector.
- **CoA timing**: time-driven events (expiration, speed windows, daily reset) fire within `samm_radius_interval_seconds` (default 30 s). Lower this in `samm.settings` for tighter enforcement.
- **Remote PostgreSQL**: the installer assumes a local PG instance. For a remote DB, update `pg_hba.conf` on the DB server and set the DSN in `/etc/samm/samm.yaml` manually after install.
- **Legacy migration**: `sql/0006..0013` and `sql/legacy_to_samm.sql` are for migrating from a pre-SAMM `public.*` schema only — do not apply on a fresh install.

---

<div align="center">

Built by [SecuryTik](https://securytik.com)

</div>
