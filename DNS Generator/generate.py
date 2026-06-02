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

# Static preamble. The "SAMM skipped" markers are honoured by the SAMM parser
# (everything between them is ignored on the SAMM side) but applied by manual
# users — keep them verbatim.
PREAMBLE = """\
# ============================================================
#  AUTO-GENERATED from "DNS Generator/catalog.json" — DO NOT EDIT BY HAND.
#  Add/remove apps in catalog.json, then run:
#      python3 "DNS Generator/generate.py"
# ============================================================

# SAMM skipped start
/ip dns
set address-list-extra-time=1d allow-remote-requests=yes cache-max-ttl=1d \\
    cache-size=10000KiB max-concurrent-queries=1000 servers=\\
    8.8.8.8,8.8.4.4,1.1.1.1
/ip firewall nat
add action=redirect chain=dstnat comment="NAT DNS to Local Router" dst-port=53 protocol=udp
# SAMM skipped end
"""

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
    out = [PREAMBLE, "", "/ip dns set address-list-extra-time=1d", ""]

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
