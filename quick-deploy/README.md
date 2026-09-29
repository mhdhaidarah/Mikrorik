# SICO Quick Deploy — RouterOS snippets

Small, self-contained RouterOS scripts you can pull straight onto a router:

```
/tool fetch url="https://raw.githubusercontent.com/mhdhaidarah/Mikrorik/main/quick-deploy/<file>" dst-path=sico.rsc mode=https; /import sico.rsc
```

Linked from the Quick Deploy section on [sico.securytik.com](https://sico.securytik.com).

| Snippet | What it does | Needs input? |
|---|---|---|
| [`sico-backup-export.rsc`](sico-backup-export.rsc) | Save a `.backup` + a readable `.rsc` export to Files. Changes nothing — run it **before** importing anything else. | no |
| [`sico-ntp-timezone.rsc`](sico-ntp-timezone.rsc) | Enable the NTP client (pool.ntp.org, Cloudflare) and auto-detect the timezone. | no |
| [`sico-l2tp-support.rsc`](sico-l2tp-support.rsc) | Dial an outbound L2TP tunnel so support can reach a router behind NAT. | yes — 3 globals |

## Two things RouterOS makes you think about

**Scripts cannot prompt.** There is no `read` in RouterOS scripting, so a snippet that
needs credentials takes them as `:global` variables set in the *same line* you paste —
see the header of `sico-l2tp-support.rsc`.

**An import runs immediately and completely.** These snippets are deliberately
*additive*: none of them sets a firewall policy, changes an interface, or touches
addressing, so none of them can lock you out. Every object they create is tagged with a
`SICO:` comment, so you can always find and remove exactly what they added:

```
/interface l2tp-client remove [find where comment="SICO:support"]
```

Run `sico-backup-export.rsc` first anyway. Written for RouterOS 7.x.
