#!/usr/bin/env zsh
set -euo pipefail

# Print CrossPoint serial logs at 115200. Overlay firmware sets ENABLE_SERIAL_LOG.
# Do not use `pio device monitor`: the port hunt drops CDC the same way upload does.

here=${0:A:h}
source "$here/usb_cdc.zsh"

if [[ ! -x $usb_cdc_python ]]; then
  print -u2 "python not found at $usb_cdc_python"
  exit 1
fi

p=$(usb_cdc_wait)
print "serial $p 115200 (quit with Ctrl-C)"
exec "$usb_cdc_python" "$here/serial_watch.py" "$p" 115200
