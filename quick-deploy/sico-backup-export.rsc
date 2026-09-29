# SICO Quick Deploy — backup & export
#
#   /tool fetch url="https://raw.githubusercontent.com/mhdhaidarah/Mikrorik/main/quick-deploy/sico-backup-export.rsc" dst-path=sico.rsc mode=https; /import sico.rsc
#
# Writes a binary backup (.backup, restores onto the SAME model) and a readable text
# export (.rsc, portable between models) into Files. Changes no running configuration —
# this is the snippet to run BEFORE you import anything else.

:local stamp ([/system clock get date] . "-" . [:pick [/system clock get time] 0 2] . [:pick [/system clock get time] 3 5])
:local name ("sico-" . [/system identity get name] . "-" . $stamp)

/system backup save name=$name
/export file=$name

:put ("SICO: wrote " . $name . ".backup and " . $name . ".rsc to Files.")
:put "SICO: download them off the router — a backup that only exists on the router is not a backup."
