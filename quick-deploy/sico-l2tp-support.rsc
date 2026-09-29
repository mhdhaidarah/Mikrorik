# SICO Quick Deploy — L2TP support tunnel (client)
#
# Dials an L2TP tunnel out to a support server so an engineer can reach this router
# even though it sits behind NAT. RouterOS scripts cannot prompt, so the three
# credentials are passed as globals in the same line you paste:
#
#   :global l2tpServer "vpn.example.com"; :global l2tpUser "support"; :global l2tpPass "secret"; /tool fetch url="https://raw.githubusercontent.com/mhdhaidarah/Mikrorik/main/quick-deploy/sico-l2tp-support.rsc" dst-path=sico.rsc mode=https; /import sico.rsc
#
# add-default-route=no on purpose: the tunnel is for INBOUND support access only. The
# router keeps its normal internet path, so importing this cannot black-hole your uplink.
# Remove it any time with:  /interface l2tp-client remove [find where comment="SICO:support"]

:global l2tpServer
:global l2tpUser
:global l2tpPass

:if ([:len $l2tpServer] = 0 || [:len $l2tpUser] = 0 || [:len $l2tpPass] = 0) do={
  :put "SICO: nothing done — set the credentials first, then import:"
  :put "SICO:   :global l2tpServer \"host\"; :global l2tpUser \"user\"; :global l2tpPass \"pass\""
} else={
  # Re-running replaces our own tunnel rather than stacking a second one.
  /interface l2tp-client remove [find where comment="SICO:support"]
  /interface l2tp-client add \
      name=sico-support \
      connect-to=$l2tpServer \
      user=$l2tpUser \
      password=$l2tpPass \
      profile=default-encryption \
      add-default-route=no \
      disabled=no \
      comment="SICO:support"

  :delay 5s
  :local st [/interface l2tp-client get [find where comment="SICO:support"] running]
  :if ($st = true) do={
    :put ("SICO: support tunnel UP to " . $l2tpServer)
  } else={
    :put ("SICO: tunnel created but not up yet — check /interface l2tp-client and /log print.")
    :put "SICO: if it authenticates then drops after ~25s, raise keepalive-timeout on the SERVER."
  }
}
