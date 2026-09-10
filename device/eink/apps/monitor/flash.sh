#!/usr/bin/env zsh
set -euo pipefail

# Build CrossPoint overlay firmware, then flash ESP32-C3 USB-CDC.
# Do not use `pio run -t upload`: PlatformIO's port hunt drops the node.

here=${0:A:h}
crosspoint=${here:h:h}/crosspoint
fw=${crosspoint}/.pio/build/default/firmware.bin
penv=${HOME}/.platformio/penv/bin
python=${penv}/python

if [[ ! -x ${penv}/esptool && ! -x ${penv}/esptool.py ]]; then
  print -u2 "esptool not found under ~/.platformio/penv/bin"
  exit 1
fi
esptool=${penv}/esptool
[[ -x $esptool ]] || esptool=${penv}/esptool.py

if [[ ${1:-} == --build || ! -f $fw ]]; then
  print "Building overlay firmware"
  (cd "$crosspoint" && pio run -e default)
fi
[[ -f $fw ]] || { print -u2 "missing $fw"; exit 1 }

port_ready() {
  local p=$1
  [[ -e $p ]] || return 1
  "$python" -c "
import serial, sys
try:
    s = serial.Serial(sys.argv[1], 115200, timeout=0.2)
    s.close()
except Exception:
    raise SystemExit(1)
" "$p"
}

print "Leave CrossPoint running on USB. Do not hold Boot unless the port never appears."
print "Waiting for a stable /dev/cu.usbmodem*"

last_fail=""
while true; do
  ports=(/dev/cu.usbmodem*(N))
  if (( ${#ports} == 0 )); then
    last_fail=""
    sleep 0.05
    continue
  fi
  p=${ports[1]}
  if [[ -n $last_fail && $p == $last_fail ]]; then
    sleep 0.1
    continue
  fi
  sleep 0.6
  [[ -e $p ]] || continue
  if ! port_ready "$p"; then
    print "stale $p"
    last_fail=$p
    while [[ -e $p ]]; do sleep 0.05; done
    last_fail=""
    continue
  fi
  print "flashing $p"
  if $esptool --chip esp32c3 --port "$p" --baud 115200 \
    --before usb-reset --after hard-reset \
    write-flash 0x10000 "$fw"; then
    print "flash ok"
    exit 0
  fi
  print "retry after disconnect"
  last_fail=$p
  while [[ -e $p ]]; do sleep 0.05; done
  last_fail=""
done
