# Shared ESP32-C3 USB-CDC helpers. Sourced by flash.sh and debug.sh.
# Do not use `pio device monitor`: PlatformIO's port hunt drops the node.

usb_cdc_python=${HOME}/.platformio/penv/bin/python

usb_cdc_port_ready() {
  local p=$1
  [[ -e $p ]] || return 1
  "$usb_cdc_python" -c "
import serial, sys
try:
    s = serial.Serial(sys.argv[1], 115200, timeout=0.2)
    s.close()
except Exception:
    raise SystemExit(1)
" "$p"
}

usb_cdc_wait() {
  print -u2 "Leave CrossPoint running on USB. Do not hold Boot unless the port never appears."
  print -u2 "Waiting for a stable /dev/cu.usbmodem*"
  local last_fail="" p
  while true; do
    local ports=(/dev/cu.usbmodem*(N))
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
    if ! usb_cdc_port_ready "$p"; then
      print -u2 "stale $p"
      last_fail=$p
      while [[ -e $p ]]; do sleep 0.05; done
      last_fail=""
      continue
    fi
    print -u2 "using $p"
    print -- "$p"
    return 0
  done
}
