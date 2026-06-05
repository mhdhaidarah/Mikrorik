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
| **Multiple PPPoE** | Ten MAC‑VLAN PPPoE clients on one SFP+ uplink, bundled into a `WAN_List` (multi‑session uplinks). |
| **DMA Radius Connect to Mikrotik** | Wire a MikroTik to an external **DMA RADIUS** server — pools, PPPoE server, NAT, expired‑user redirect. |
| **User Manager Radius Setup** | RouterOS **User Manager** as the RADIUS source: rate limitations, priced/validity profiles and router binding. |
| **DHCP Speed Limit** | One‑liner DHCP lease script that auto‑creates/removes a per‑client simple queue. |
| **Mirktoik OSPF.txt** | Minimal OSPF instance/area/interface templates (normal router + default‑route originator). |
| **wgcf.zip** | `wgcf` helper binary (generate WireGuard/Cloudflare WARP configs). |

> ⚠️ **Templates, not secrets.** Some RADIUS examples ship with placeholder
> shared secrets and IPs. Always replace credentials, address ranges and
> interface names with your own before deploying to production.

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
