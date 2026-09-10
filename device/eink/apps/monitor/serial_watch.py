#!/usr/bin/env python3
"""Print USB-CDC until the device sleeps, resets, or unplugs."""

import sys

import serial


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: serial_watch.py PORT BAUD", file=sys.stderr)
        return 2
    port = sys.argv[1]
    baud = int(sys.argv[2])
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
    except serial.SerialException as exc:
        print(f"open failed: {exc}", file=sys.stderr)
        return 1
    print(f"serial {port} {baud} (quit with Ctrl-C)", file=sys.stderr)
    try:
        while True:
            try:
                data = ser.read(ser.in_waiting or 1)
            except (OSError, serial.SerialException):
                print("\nserial gone (sleep, reset, or unplug)", file=sys.stderr)
                return 0
            if data:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 0
    finally:
        try:
            ser.close()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
