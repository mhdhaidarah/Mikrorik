# DNS Generator

Single source of truth for the **IP Collector DNS** monitoring script.

Instead of hand-editing the 350-line RouterOS file, all apps/sites live in
**`catalog.json`**. A small generator turns that into the `.rsc` file at the
repo root, so:

- **Manual MikroTik users** keep downloading `../IP Collector DNS` exactly as before.
- **SAMM** keeps fetching that same root file via *DNS → Websites & App Filter → Update from repo*.
- Adding an app = one entry in `catalog.json` (no copy-paste, no drift).

## Usage

```bash
python3 "DNS Generator/generate.py"
```

This regenerates `../IP Collector DNS` from `catalog.json`. Commit both.

## Catalog format

```json
{
  "apps": [
    {
      "slug": "youtube",            // SAMM slug (lowercase, dashes)
      "label": "Youtube",           // address-list = "<label> IPs"
      "section": "YOUTUBE / GOOGLE VIDEO",
      "category": "streaming",      // SAMM QoS category
      "priority": 6,                // SAMM QoS default slot 1-8
      "domains": ["youtube.com", "googlevideo.com"],
      "cidrs": []                   // optional published IP ranges
    }
  ],
  "games": [
    { "slug": "pubg-mobile", "label": "PUBG Mobile", "category": "gaming",
      "priority": 4, "protocol": "tcp", "ports": "10012,17500" }
  ]
}
```

### To add an app
1. Copy an existing entry in `catalog.json`, change `label`, `domains`,
   `category`, `priority`.
2. Run the generator.
3. Commit `catalog.json` + the regenerated `IP Collector DNS`.

The IPs themselves are **not** stored here — they're collected live on each
router from real DNS lookups. The catalog only defines *which* apps to watch.

## `settings` block (advanced)

```json
"settings": {
  "ipv6_counters": true,          // emit /ipv6 firewall mangle counters too
  "anti_bypass": {
    "force_dns_tcp": true,        // also redirect TCP/53 (not just UDP)
    "block_dot": true,            // drop DNS-over-TLS (port 853)
    "block_doh": true,            // collect DoH endpoints + drop 443 to them
    "fasttrack_note": true,       // emit the fasttrack-accuracy guidance comment
    "doh_servers": ["dns.google", "cloudflare-dns.com", ...]
  }
}
```

All anti-bypass output lives **inside the `# SAMM skipped` block**, so SAMM's
own push is unaffected — it only applies when a manual user pastes the whole
file. The IPv6 counters and DoH lines are also ignored by SAMM's parser today
(SAMM reads only `/ip ...`), so they're additive and safe.

**Caveats for manual users:** the DoT/DoH drop rules append to the `forward`
chain — make sure they sit above any blanket accept. IPv6 counters need the
IPv6 package enabled. The fasttrack fix is order-sensitive and ships as a
commented note, not an auto-injected rule.
