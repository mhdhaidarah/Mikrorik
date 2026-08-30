<div align="center">

<img src=".assets/samm-logo.svg" width="96" height="96" alt="SAMM logo" />

# Mikrorik — MikroTik / RouterOS Config Library

**Ready-to-paste RouterOS scripts for ISPs and networks, plus the live app/website
catalog that powers [SAMM](https://samm.securytik.com)'s monitoring & QoS.**

[![Website](https://img.shields.io/badge/SAMM-samm.securytik.com-3b82f6?style=flat-square)](https://samm.securytik.com)
[![SecuryTik](https://img.shields.io/badge/SecuryTik-securytik.com-22d3ee?style=flat-square)](https://securytik.com)

</div>

---

## What's here

A collection of battle-tested MikroTik (RouterOS) configuration snippets used by
[SecuryTik](https://securytik.com) when deploying ISP, hotspot and enterprise
routers — plus the **IP Collector DNS** script and its generator, which are the
single source of truth for the app/website lists that
[**SAMM** (SecuryTik Active Mikrotik Manager)](https://samm.securytik.com) uses to
identify and shape traffic.

Most files are plain RouterOS scripts: open them, review the values, and paste
into the MikroTik terminal (or `/import` them). They are **templates** — adjust
addresses, interfaces and credentials to your network before applying.

| File | What it does |
|---|---|
| **IP Collector DNS** | Auto-generated RouterOS script that collects per‑app/website IPs from live DNS lookups into address‑lists, with Up/Down traffic counters. Consumed by SAMM (*Websites & App Filter → Update from repo*) and usable stand‑alone. **Do not edit by hand** — see [DNS Generator](#dns-generator). |
| **DNS Generator/** | Python tool + `catalog.json` that generate `IP Collector DNS`. Add an app in one place, regenerate, done. |
| **Basic Router with Vlans** | Full bootstrap for a single‑bridge, VLAN‑filtered router (Server / Office / Staff / Guest zones) with per‑VLAN gateways. |
| **Basic ISP PPPoE Hotspot** | PPPoE server + Hotspot starter with RADIUS and a ladder of rate‑limit profiles (1M–30M). |
| **User Manager Radius Setup** | RouterOS **User Manager** as the RADIUS source: rate limitations, priced/validity profiles and router binding. |
| **DMA Radius Connect to Mikrotik** | Wire a MikroTik to an external **DMA RADIUS** server — pools, PPPoE server, NAT, expired‑user redirect. |
| **Multiple PPPoE** | Ten MAC‑VLAN PPPoE clients on one SFP+ uplink, bundled into a `WAN_List` (multi‑session uplinks). |
| **Mirktoik OSPF.txt** | Minimal OSPF instance/area/interface templates (normal router + default‑route originator). |
| **VPN Server** | L2TP/IPsec + WireGuard server bootstrap with dual‑stack addressing. |
| **DHCP Speed Limit** | Paste‑in‑Terminal command: attaches a lease‑script to **every** DHCP server so each client gets its own parent‑less simple queue (default 2M/2M, one line to change). Verified on ROS 7.23. |
| **wgcf.zip** | `wgcf` helper binary (generate WireGuard/Cloudflare WARP configs). |

### Security scripts

Two ways to use them, **same result either way**:

* **`Security Firewall`** — one file with everything, conflict-checked on real
  RouterOS. Paste it and you are done.
* **`Security 01…11`** — the same protections as separate files, numbered in a
  sensible paste order. Order does not actually affect the result (each is
  order-independent), the numbers just show the natural sequence.

Every file was import-tested on RouterOS 7.23; the four attack scripts were
verified with a real attacker (nmap, nping, a DHCP-starvation flood). All are
interface-independent — no interface name, no interface list to build first —
except **11**, which needs to know the WAN and says so.

**Put your own IP in the `Trusted` list before pasting the SSH block, and read
the top of each file.**

| File | What it does |
|---|---|
| **Security Firewall** | All of 01–10 in one paste, in the correct order, conflict-free. The all-in-one. |
| **Security 01 Connection Tracking** | The base every firewall needs: accept established/related/untracked, drop invalid, on `input` and `forward`. |
| **Security 02 Router Hardening** | Turns off unused attack surface: telnet, ftp, www(-ssl), bandwidth-server, mac-ping, neighbour discovery, proxy, socks; SSH strong-crypto on. API (8728) kept for SAMM. |
| **Security 03 Bogon Source Drop** | Drops packets whose **source** is a reserved/martian range. RFC1918/CGNAT left out — add them only if every WAN is public. |
| **Security 04 DNS Flood Attack** | Stops the router being an open resolver: transit passes, `DNS-CLIENTS` (RFC1918 + CGNAT) rate-limited per source, flooders flagged 10m, everything else dropped (TCP + UDP). |
| **Security 05 ICMP Policy** | Rate-limited ping plus the ICMP types that must never drop (fragmentation-needed, TTL-exceeded). |
| **Security 06 SSH Brute Force** | Staged blacklist on SSH **and WinBox** (22, 8291): `Trusted` always allowed, three 1-minute stages, then a 1-day ban. *Verified — it will lock you out if your IP isn't in `Trusted`.* |
| **Security 07 DDoS Connection Rate** | Flags any source opening connections faster than 32/10s and drops it 10m — catches floods the SYN rules miss. |
| **Security 08 SYN Attack** | `tcp-syncookies` on, plus a `syn-attack` chain: SYN under 400/s **returns** (so it composes with the scan/DDoS detectors), the flood is dropped. *Verified: 1 058 of a flood dropped.* |
| **Security 09 Port Scan Attack** | PSD scan detector on `input` and `forward`; offenders land in `Port-Scan` for 1 day and are dropped. *Verified against nmap `-sS`.* |
| **Security 10 DHCP Starvation Attack** | Rate-limits DHCP DISCOVERs so a spoofed-MAC flood can't drain the pool; `conflict-detection` on. *Verified: 14 373 of 14 574 spoofed DISCOVERs dropped, 0 leases lost.* |
| **Security 11 Unsolicited Forward Drop** | Stateful edge — nothing new comes in from the WAN unless port-forwarded. **The one file that needs your WAN interface** (the interface-free form also drops your LAN's outbound UDP), so it's not in `Security Firewall`. |
| **Security Port Knocking** | Hides SSH + WinBox behind a 3-knock sequence (default **7555 → 9555 → 8555**, change them). **An alternative to 06 — use one, not both** — so it's a separate file, not in the bundle. *Verified: knock opened access, no knock stayed shut.* |

---

## IP Collector DNS + SAMM

`IP Collector DNS` turns each app/website into a RouterOS DNS‑static collector
that builds an address‑list (`"<App> IPs"`) from real client lookups, then mangles
per‑app **Traffic Up / Traffic Down** counters. Two audiences consume the same
file at the same path:

- **SAMM** fetches it and pushes the DNS‑static, address‑list and mangle rules to
  managed routers automatically.
- **Manual users** paste the whole `.rsc` straight onto RouterOS.

Anything that only manual users need — the DNS‑redirect preamble, anti‑bypass
rules, IPv6 counters, and the **download packet‑mark** rules — lives inside a
`# SAMM skipped … # SAMM skipped end` block, which SAMM's parser ignores. That
keeps the two use‑cases from stepping on each other.

### Download packet marks (QoS seed)

The generator emits one **disabled** `mark-packet` rule per app/website on the
download direction (`new-packet-mark="<App> download"`). They're a ready‑made
starting point for a QoS queue tree: enable the rules you want and point a queue
at the matching packet mark. Because they sit in the `# SAMM skipped` block,
SAMM never touches them.

---

## DNS Generator

Don't hand‑edit `IP Collector DNS`. Everything lives in
[`DNS Generator/catalog.json`](DNS%20Generator/catalog.json):

```bash
# 1. add / edit an app in DNS Generator/catalog.json
# 2. regenerate the RouterOS script at the repo root
python3 "DNS Generator/generate.py"
# 3. commit catalog.json + the regenerated IP Collector DNS
```

See [`DNS Generator/README.md`](DNS%20Generator/README.md) for the catalog format
and the advanced `settings` block (anti‑bypass, IPv6 counters, download packet
marks).

---

## Links

- 🌐 **SAMM** — MikroTik AAA, monitoring & QoS: **https://samm.securytik.com**
- 🏢 **SecuryTik** — the company behind it: **https://securytik.com**

---

<div align="center">

Maintained by **Mohammed Haidar** · Beirut, Lebanon · 📞 +961 81 507 933

</div>
