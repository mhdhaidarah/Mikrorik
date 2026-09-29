# SICO Quick Deploy — NTP + timezone
#
#   /tool fetch url="https://raw.githubusercontent.com/mhdhaidarah/Mikrorik/main/quick-deploy/sico-ntp-timezone.rsc" dst-path=sico.rsc mode=https; /import sico.rsc
#
# Additive and safe to re-run: touches only the NTP client and the clock. It does not
# change any interface, address or firewall rule, so it cannot lock you out.
# Every object it creates is tagged SICO:ntp.

/system ntp client set enabled=yes

# Re-running must not stack duplicate servers — drop our own entries first.
:foreach s in=[/system/ntp/client/servers/find where comment="SICO:ntp"] do={
  /system/ntp/client/servers/remove $s
}
/system/ntp/client/servers/add address=pool.ntp.org comment="SICO:ntp"
/system/ntp/client/servers/add address=time.cloudflare.com comment="SICO:ntp"

# Let the router work its own zone out from its public IP.
/system clock set time-zone-autodetect=yes

:put "SICO: NTP client enabled (pool.ntp.org, time.cloudflare.com), timezone auto-detect on."
:put ("SICO: clock now " . [/system clock get date] . " " . [/system clock get time])
