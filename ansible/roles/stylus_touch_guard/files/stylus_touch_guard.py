#!/usr/bin/env python3
"""Disable touchscreen while a Wacom stylus is in proximity (Yoga / Xournal++).

Ported from ditschi/helpers-and-automation (Yoga L13 Thinkpad).
Device nodes are resolved by name so /dev/input/eventN renumbering is fine.
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from evdev import InputDevice, list_devices
import psutil
import subprocess

TOUCHSCREEN_LOCK_DELAY = 2.0
STYLUS_NAME_HINTS = ("stylus", "pen")
TOUCH_NAME_HINTS = ("finger", "touchscreen", "touch digitizer", "touch")
EXCLUDE_HINTS = ("keyboard", "consumer control", "trackpoint", "mouse")


def log(msg: str) -> None:
    print(msg, flush=True)


def _name_matches(name: str, hints: tuple[str, ...]) -> bool:
    lower = name.lower()
    if any(x in lower for x in EXCLUDE_HINTS):
        return False
    return any(h in lower for h in hints)


def find_device(hints: tuple[str, ...], prefer_wacom: bool = True) -> Optional[InputDevice]:
    candidates: list[InputDevice] = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        if not _name_matches(dev.name, hints):
            continue
        candidates.append(dev)
    if not candidates:
        return None
    if prefer_wacom:
        for dev in candidates:
            if "wacom" in dev.name.lower():
                return dev
    return candidates[0]


def find_evtest_pid(device_path: str) -> Optional[int]:
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = proc.info.get("cmdline") or []
        if (
            len(cmdline) >= 3
            and cmdline[0] == "evtest"
            and "--grab" in cmdline
            and device_path in cmdline
        ):
            return int(proc.info["pid"])
    return None


def disable_touch(touch_path: str, debug: bool = False) -> None:
    if find_evtest_pid(touch_path):
        if debug:
            log("Touch already grabbed")
        return
    cmd = ["evtest", "--grab", touch_path]
    if debug:
        log(f"Running: {' '.join(cmd)}")
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.3)
    if find_evtest_pid(touch_path):
        log(f"Touch disabled via grab on {touch_path}")
    else:
        log(f"Failed to grab touch device {touch_path}")


def enable_touch(touch_path: str, debug: bool = False) -> None:
    pid = find_evtest_pid(touch_path)
    if not pid:
        if debug:
            log("Touch already enabled")
        return
    try:
        psutil.Process(pid).kill()
        log(f"Touch enabled (killed evtest pid {pid})")
    except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
        log(f"Could not kill evtest {pid}: {exc}")


def stylus_close(stylus: InputDevice) -> bool:
    try:
        return bool(stylus.active_keys())
    except OSError:
        return False


def resolve_devices(debug: bool = False) -> tuple[InputDevice, str]:
    stylus = find_device(STYLUS_NAME_HINTS)
    touch = find_device(TOUCH_NAME_HINTS)
    if not stylus or not touch:
        raise RuntimeError(
            "Could not find stylus/touch devices. "
            f"stylus={getattr(stylus, 'name', None)!r} "
            f"touch={getattr(touch, 'name', None)!r}. "
            "Check: python3 -c \"from evdev import list_devices, InputDevice; "
            "[print(InputDevice(p).name, p) for p in list_devices()]\""
        )
    if stylus.path == touch.path:
        raise RuntimeError(f"Stylus and touch resolved to the same device: {stylus.path}")
    if debug:
        log(f"Stylus: {stylus.name} ({stylus.path})")
        log(f"Touch:  {touch.name} ({touch.path})")
    return stylus, touch.path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Disable touchscreen while stylus is in proximity"
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--test-proximity",
        action="store_true",
        help="Print proximity state once per second",
    )
    parser.add_argument(
        "--once-resolve",
        action="store_true",
        help="Resolve devices and exit (for ansible/CI checks)",
    )
    args = parser.parse_args()

    while True:
        try:
            stylus, touch_path = resolve_devices(debug=args.debug)
            break
        except RuntimeError as exc:
            log(str(exc))
            if args.once_resolve:
                return 1
            log("Retrying device resolve in 30s…")
            time.sleep(30)

    if args.once_resolve:
        log(f"OK stylus={stylus.name} touch={touch_path}")
        return 0

    while True:
        if args.test_proximity:
            log(f"Stylus close: {stylus_close(stylus)}")
            time.sleep(1)
            continue
        if stylus_close(stylus):
            disable_touch(touch_path, debug=args.debug)
        else:
            time.sleep(TOUCHSCREEN_LOCK_DELAY)
            if not stylus_close(stylus):
                enable_touch(touch_path, debug=args.debug)
        time.sleep(0.05)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
