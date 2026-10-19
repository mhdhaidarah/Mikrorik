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
    # Resolvers: Google + Cloudflare, IPv4 then IPv6. RouterOS uses the IPv6
    # entries only when the router actually has IPv6 upstream; harmless otherwise.
    o = ["# SAMM skipped start",
         "/ip dns",
         "set address-list-extra-time=1d allow-remote-requests=yes cache-max-ttl=1d \\",
         "    cache-size=10000KiB max-concurrent-queries=1000 servers=\\",
         "    8.8.8.8,8.8.4.4,1.1.1.1,2001:4860:4860::8888,2001:4860:4860::8844,2606:4700:4700::1111,2606:4700:4700::1001"]

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

    # OS connectivity-check passthrough. Forcing client DNS through this router
    # routes each OS's "is there internet?" probe through us; if any probe host
    # gets collected/mangled the device shows a false "No internet access" /
    # captive-portal popup despite working internet. Windows checks an EXACT IP
    # (pin it via 'static'); Apple just needs to reach the real CDN (resolve via
    # 'forward', never pin). An exact entry here also overrides any
    # match-subdomain collector (e.g. apple.com sweeping in captive.apple.com).
    cp = (settings or {}).get("connectivity_passthrough", {})
    if cp.get("enabled", True):
        statics = cp.get("static", [])
        forwards = cp.get("forward", [])
        if statics or forwards:
            o += ["", "# OS connectivity probes — answer/forward cleanly so devices see 'Internet access'",
                  "/ip dns static"]
            for s in statics:
                o.append(f'add name={s["host"]} address={s["ip"]} '
                         f'comment="connectivity probe — do not collect"')
            fwd_to = cp.get("forward_to", "8.8.8.8")
            for f in forwards:
                o.append(f'add name={f["host"]} type=FWD forward-to={fwd_to} '
                         f'comment="connectivity probe — do not collect"')

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


def port_rules(g):
    """[(protocol, ports)] of a game: "tcp"/"udp" keys, or the older single
    protocol + ports pair."""
    rules = [(p, g[p]) for p in ("tcp", "udp") if g.get(p)]
    if not rules and g.get("protocol") and g.get("ports"):
        rules = [(g["protocol"], g["ports"])]
    return rules


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
    # Games may carry domains too: a game's lobby/match servers are often
    # found by name (game.clashofclans.com), which is far more precise than a
    # port range shared with every other app on the Internet.
    for a in apps + [g for g in games if g.get("domains")]:
        lst = f'{a["label"]} IPs'
        sec = a.get("section") or (f'GAME: {a["label"]}' if a in games else a["label"])
        if sec != last_section:
            out.append(banner(sec))
            last_section = sec
        ms = "yes" if a.get("match_subdomain", True) else "no"
        for d in a["domains"]:
            out.append(f'add address-list="{lst}" comment="{lst}" '
                       f'match-subdomain={ms} name={d} type=FWD')
    out.append("")

    # ---- Static CIDR ranges ----
    cidr_apps = [a for a in apps + games if a.get("cidrs")]
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
            # connection-state=new: the address only has to be learnt once per
            # flow, so the rule runs on one packet per connection instead of
            # every packet of every game session (router CPU).
            for proto, ports in port_rules(g):
                out.append(
                    f'/ip firewall mangle add chain=prerouting '
                    f'action=add-dst-to-address-list address-list="{lst}" '
                    f'address-list-timeout=1d protocol={proto} '
                    f'dst-port={ports} comment="{lst}" '
                    f'connection-state=new dst-address-type=!local')
        out.append("")

    # ---- Download packet marks (disabled — manual QoS starting point) ----
    # One mark-packet rule per app/website on the DOWNLOAD (to-client)
    # direction, mirroring the Up/Down counter set (all apps + measured games).
    # Wrapped in a '# SAMM skipped' block on purpose: SAMM's parser drops
    # everything between the markers, so it never pushes, wipes, or counts
    # these — they exist purely for manual full-file users who paste the .rsc
    # straight onto RouterOS and want a QoS queue-tree seed. Created DISABLED
    # so nothing changes until the operator enables a rule and attaches a queue.
    if settings.get("download_packet_marks", True):
        out.append("# SAMM skipped start")
        out.append(banner("DOWNLOAD PACKET MARKS (disabled — manual QoS only)"))
        out.append("/ip firewall mangle")

        def dmark(label):
            lst = f'{label} IPs'
            out.append(
                f'add action=mark-packet chain=prerouting '
                f'comment="{label} Download Mark" disabled=yes '
                f'new-packet-mark="{label} download" passthrough=yes '
                f'src-address-list="{lst}"')

        for a in apps:
            dmark(a["label"])
        for g in game_counters:
            dmark(g["label"])
        out.append("# SAMM skipped end")
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


# The categories SAMM knows how to render. A category is not free-form: SAMM
# groups the App Filter and QoS screens by it (_APP_CAT_ORDER), gives each one a
# translated heading (_app_cat_label) and a chip colour. Ship a category SAMM
# has never heard of and the apps in it fall to the bottom of the list with an
# untinted chip and a Title-Cased fallback heading — it looks like a rendering
# bug, and nothing here would have told you. So validate on the way out, and
# when you add one, add it to SAMM in the same change.
CATEGORIES = {
    "messaging", "finance", "conferencing", "ai", "social", "streaming",
    "gaming", "store", "productivity", "download", "vpn", "speedtest", "other",
}
PRIORITY_RANGE = range(1, 9)      # SAMM QoS has eight slots


def validate(catalog):
    """Fail loudly on anything SAMM could not render. Cheap, and it catches the
    typo'd category / out-of-range priority that otherwise ships silently."""
    errors, seen = [], set()
    for a in catalog["apps"] + catalog.get("games", []):
        slug = a.get("slug", "<missing slug>")
        if not a.get("slug") or not a.get("label"):
            errors.append(f"{slug}: slug and label are both required")
        if slug in seen:
            errors.append(f"{slug}: duplicate slug")
        seen.add(slug)
        cat = a.get("category")
        if cat not in CATEGORIES:
            errors.append(
                f"{slug}: category {cat!r} is not one SAMM renders — "
                f"add it to _APP_CAT_ORDER, _app_cat_label and the QoS chip "
                f"colours in SAMM first, then list it in CATEGORIES here")
        if a.get("priority") not in PRIORITY_RANGE:
            errors.append(f"{slug}: priority {a.get('priority')!r} is outside 1-8")
    for a in catalog["apps"]:
        if not a.get("domains"):
            errors.append(f"{a.get('slug')}: an app with no domains collects nothing")
    for g in catalog.get("games", []):
        if not (g.get("domains") or g.get("cidrs") or port_rules(g)):
            errors.append(f"{g.get('slug')}: a game with no domains, cidrs or ports collects nothing")
    # One domain, one app. A domain listed twice — or listed under one app while
    # its parent is under another (match-subdomain) — puts the same addresses in
    # two lists, so the same bytes are counted, and shaped, twice.
    owner = {}
    for a in catalog["apps"] + catalog.get("games", []):
        for d in a.get("domains") or []:
            d = d.lower().strip(".")
            if d in owner and owner[d] != a["slug"]:
                errors.append(f"{a['slug']}: {d} is already listed under {owner[d]}")
            owner.setdefault(d, a["slug"])
    for d, slug in owner.items():
        parts = d.split(".")
        for i in range(1, len(parts) - 1):
            parent = ".".join(parts[i:])
            if owner.get(parent) not in (None, slug):
                errors.append(f"{slug}: {d} sits under {parent}, which belongs to {owner[parent]}")
    if errors:
        raise SystemExit("catalog.json is not valid:\n  - " + "\n  - ".join(errors))


def refresh_cidrs(catalog):
    """Rewrite each entry's `cidrs` from the prefixes its `asns` announce today
    (RIPEstat), IPv4 only, aggregated. Only for networks that carry nothing but
    that service (Netflix Open Connect, Roblox, Riot, Valve, Telegram...) — a
    cloud or CDN ASN would sweep in thousands of unrelated sites. Network is
    used here and only here: plain generation stays offline and repeatable."""
    import ipaddress
    import urllib.request
    for a in catalog["apps"] + catalog.get("games", []):
        if not a.get("asns"):
            continue
        nets = [ipaddress.ip_network(c) for c in a.get("cidrs_extra", [])]
        for asn in a["asns"]:
            url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.load(r)["data"]
            got = [ipaddress.ip_network(p["prefix"]) for p in data["prefixes"] if ":" not in p["prefix"]]
            if not got:
                raise SystemExit(f"{a['slug']}: AS{asn} announces no IPv4 prefix — refusing to empty its list")
            nets += got
        a["cidrs"] = [str(n) for n in ipaddress.collapse_addresses(nets)]
        print(f"  {a['slug']}: {len(a['cidrs'])} ranges from AS{', AS'.join(map(str, a['asns']))}")
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    import sys
    with open(CATALOG, encoding="utf-8") as f:
        catalog = json.load(f)
    if "--refresh-cidrs" in sys.argv[1:]:
        refresh_cidrs(catalog)
    validate(catalog)
    text = build(catalog)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    napps = len(catalog["apps"])
    ngames = len(catalog.get("games", []))
    ndomains = sum(len(a["domains"]) for a in catalog["apps"])
    print(f"Wrote {os.path.relpath(OUT)} — {napps} apps, {ndomains} domains, {ngames} games")


if __name__ == "__main__":
    main()
