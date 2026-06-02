#!/usr/bin/env python3
"""Generate the 'IP Collector DNS' RouterOS script from catalog.json.

Single source of truth = catalog.json (in this folder). Edit that, then run:

    python3 "DNS Generator/generate.py"

The generated .rsc is written to the REPO ROOT (parent of this folder) so the
manual MikroTik users keep grabbing the same file at the same path. SAMM's
"Update from repo" also fetches that root file unchanged.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
OUT = os.path.join(HERE, "..", "IP Collector DNS")

HEADER = """\
# ============================================================
#  AUTO-GENERATED from "DNS Generator/catalog.json" — DO NOT EDIT BY HAND.
#  Add/remove apps in catalog.json, then run:
#      python3 "DNS Generator/generate.py"
# ============================================================"""


def build_preamble(settings):
    """The '# SAMM skipped' block: router DNS config + anti-bypass module.
    Everything here is IGNORED by SAMM's parser (SAMM does its own DNS-redirect
    via the wizard); it's for manual full-file users who want clients forced
    through this router so the collectors actually see the lookups."""
    ab = (settings or {}).get("anti_bypass", {})
    o = ["# SAMM skipped start",
         "/ip dns",
         "set address-list-extra-time=1d allow-remote-requests=yes cache-max-ttl=1d \\",
         "    cache-size=10000KiB max-concurrent-queries=1000 servers=\\",
         "    8.8.8.8,8.8.4.4,1.1.1.1"]

    # Force DNS through the router (UDP always; TCP closes a common bypass).
    o += ["", "# Force all client DNS through this router so the collectors see it",
          "/ip firewall nat",
          'add action=redirect chain=dstnat comment="NAT DNS to Local Router (UDP)" dst-port=53 protocol=udp']
    if ab.get("force_dns_tcp"):
        o.append('add action=redirect chain=dstnat comment="NAT DNS to Local Router (TCP)" dst-port=53 protocol=tcp')

    # Collect DoH endpoint IPs from their hostnames so we can drop them.
    doh = ab.get("doh_servers") or []
    if ab.get("block_doh") and doh:
        o += ["", "# Collect DNS-over-HTTPS endpoint IPs (so we can block them below)",
              "/ip dns static"]
        for h in doh:
            o.append(f'add address-list="DoH Servers" comment="DoH Servers" '
                     f'match-subdomain=yes name={h} type=FWD')

    # Drop encrypted DNS so clients fall back to plaintext via this router.
    if ab.get("block_dot") or ab.get("block_doh"):
        o += ["", "# Block encrypted DNS (DoT/DoH) — REVIEW: these append to the",
              "# forward chain; make sure they sit ABOVE any blanket accept.",
              "/ip firewall filter"]
        if ab.get("block_dot"):
            o.append('add action=drop chain=forward comment="Block DoT (DNS over TLS)" protocol=tcp dst-port=853')
            o.append('add action=drop chain=forward comment="Block DoT (DNS over TLS, UDP)" protocol=udp dst-port=853')
        if ab.get("block_doh") and doh:
            o.append('add action=drop chain=forward comment="Block DoH (DNS over HTTPS)" protocol=tcp dst-port=443 dst-address-list="DoH Servers"')

    # Fasttrack note — order-sensitive, so guidance only (not auto-injected).
    if ab.get("fasttrack_note"):
        o += ["",
              "# >>> ACCURACY NOTE: if you run a 'fasttrack-connection' rule, established",
              "#     flows BYPASS these mangle counters and the SAMM QoS queue tree. To fix,",
              "#     add accept rules for the monitored lists ABOVE your fasttrack rule, e.g.:",
              "#       /ip firewall filter",
              '#       add chain=forward action=accept connection-state=established,related \\',
              '#           src-address-list="Youtube IPs"   comment="no-fasttrack: monitored"',
              "#     (repeat per list, or maintain one combined list). Left commented on purpose."]

    o.append("# SAMM skipped end")
    return "\n".join(o)


FOOTER = """\
#by Mohammed Haidar
#+961 81507933
#Beirut Lebanon
"""


def banner(text):
    return f"# ===================== {text} ====================="


def build(catalog):
    apps = catalog["apps"]
    games = catalog.get("games", [])
    settings = catalog.get("settings", {})
    out = [HEADER, "", build_preamble(settings), "",
           "/ip dns set address-list-extra-time=1d", ""]

    # ---- DNS static (the IP collectors) ----
    out.append("/ip dns static")
    last_section = None
    for a in apps:
        lst = f'{a["label"]} IPs'
        sec = a.get("section") or a["label"]
        if sec != last_section:
            out.append(banner(sec))
            last_section = sec
        ms = "yes" if a.get("match_subdomain", True) else "no"
        for d in a["domains"]:
            out.append(f'add address-list="{lst}" comment="{lst}" '
                       f'match-subdomain={ms} name={d} type=FWD')
    out.append("")

    # ---- Static CIDR ranges ----
    cidr_apps = [a for a in apps if a.get("cidrs")]
    if cidr_apps:
        out.append("/ip firewall address-list")
        for a in cidr_apps:
            lst = f'{a["label"]} IPs'
            for c in a["cidrs"]:
                out.append(f'add address={c} list="{lst}"')
        out.append("")

    # ---- Per-app traffic counters ----
    out.append("/ip firewall mangle")
    out.append("# Traffic Monitor — wipe previous SAMM counters before re-adding")
    out.append('remove [find where comment~"Traffic"]')
    def counters(label):
        lst = f'{label} IPs'
        out.append(f'# {label}')
        out.append(f'add action=passthrough chain=prerouting '
                   f'comment="{label} Traffic Down" src-address-list="{lst}"')
        out.append(f'add action=passthrough chain=prerouting '
                   f'comment="{label} Traffic Up" dst-address-list="{lst}"')

    for a in apps:
        counters(a["label"])
    # Games that opt into measurement get the same Up/Down counters.
    game_counters = [g for g in games if g.get("counter")]
    if game_counters:
        out.append("# --- game traffic counters ---")
        for g in game_counters:
            counters(g["label"])
    out.append("")

    # ---- Games: port-based collectors ----
    if games:
        out.append(banner("GAMES"))
        for g in games:
            lst = f'{g["label"]} IPs'
            out.append(
                f'/ip firewall mangle add chain=prerouting '
                f'action=add-dst-to-address-list address-list="{lst}" '
                f'address-list-timeout=1d protocol={g["protocol"]} '
                f'dst-port={g["ports"]} comment="{lst}" dst-address-type=!local')
        out.append("")

    # ---- IPv6 counters (optional) ----
    # Mirror of the v4 counters on the IPv6 firewall. SAMM ignores all /ipv6
    # lines today, so this is additive; it benefits manual users now and sets
    # up SAMM v6 support later. NOTE: requires the IPv6 package enabled and
    # RouterOS populating v6 address-lists from DNS — otherwise it's a no-op.
    if settings.get("ipv6_counters"):
        out.append(banner("IPv6 COUNTERS (optional — requires IPv6 enabled)"))
        out.append("/ipv6 firewall mangle")
        out.append('remove [find where comment~"Traffic"]')
        for a in apps:
            counters(a["label"])
        for g in [g for g in games if g.get("counter")]:
            counters(g["label"])
        out.append("")

    out.append(FOOTER)
    return "\n".join(out) + "\n"


def main():
    with open(CATALOG, encoding="utf-8") as f:
        catalog = json.load(f)
    text = build(catalog)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    napps = len(catalog["apps"])
    ngames = len(catalog.get("games", []))
    ndomains = sum(len(a["domains"]) for a in catalog["apps"])
    print(f"Wrote {os.path.relpath(OUT)} — {napps} apps, {ndomains} domains, {ngames} games")


if __name__ == "__main__":
    main()
