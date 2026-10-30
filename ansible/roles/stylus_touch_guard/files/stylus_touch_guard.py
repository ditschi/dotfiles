#!/usr/bin/env python3
"""Disable touchscreen while a Wacom stylus is in proximity (Yoga / Xournal++).

Ported from ditschi/helpers-and-automation (Yoga L13 Thinkpad).
Device nodes are resolved by name so /dev/input/eventN renumbering is fine.
"""
from __future__ import annotations

import argparse
import time
from typing import Callable, Optional

from evdev import InputDevice, ecodes, list_devices
import psutil
import subprocess

TOUCHSCREEN_LOCK_DELAY = 2.0
# Name fallbacks for devices whose capabilities cannot be read. The Wacom
# touchscreen is called "Wacom Pen and multitouch sensor Finger", so the
# stylus hint must match a trailing "pen", not the substring.
STYLUS_NAME_SUFFIXES = (" pen", " stylus")
TOUCH_NAME_HINTS = ("finger", "touchscreen", "touch digitizer")
EXCLUDE_HINTS = ("keyboard", "consumer control", "trackpoint", "mouse", "touchpad")


def log(msg: str) -> None:
    print(msg, flush=True)


def _excluded(dev: InputDevice) -> bool:
    lower = dev.name.lower()
    return any(x in lower for x in EXCLUDE_HINTS)


def _capabilities(dev: InputDevice) -> tuple[set[int], set[int], set[int]]:
    """Return (key codes, abs codes, input props); empty if unreadable."""
    try:
        caps = dev.capabilities(absinfo=False)
        props = dev.input_props()
    except OSError:
        return set(), set(), set()
    return (
        set(caps.get(ecodes.EV_KEY, ())),
        set(caps.get(ecodes.EV_ABS, ())),
        set(props),
    )


def is_stylus(dev: InputDevice) -> bool:
    if _excluded(dev):
        return False
    keys, _, _ = _capabilities(dev)
    if ecodes.BTN_TOOL_PEN in keys:
        return True
    return dev.name.lower().endswith(STYLUS_NAME_SUFFIXES)


def is_touchscreen(dev: InputDevice) -> bool:
    """Direct-touch multitouch device; never a touchpad or the stylus."""
    if _excluded(dev) or is_stylus(dev):
        return False
    _, absolute, props = _capabilities(dev)
    if ecodes.INPUT_PROP_POINTER in props:
        return False
    if ecodes.INPUT_PROP_DIRECT in props and ecodes.ABS_MT_POSITION_X in absolute:
        return True
    lower = dev.name.lower()
    return any(h in lower for h in TOUCH_NAME_HINTS)


def find_device(
    matches: Callable[[InputDevice], bool], prefer_wacom: bool = True
) -> Optional[InputDevice]:
    candidates: list[InputDevice] = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except OSError:
            continue
        if not matches(dev):
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
    stylus = find_device(is_stylus)
    touch = find_device(is_touchscreen)
    if not stylus or not touch:
        raise RuntimeError(
            "Could not find stylus/touch devices. "
            f"stylus={getattr(stylus, 'name', None)!r} "
            f"touch={getattr(touch, 'name', None)!r}. "
            'Check: python3 -c "from evdev import list_devices, InputDevice; '
            '[print(InputDevice(p).name, p) for p in list_devices()]"'
        )
    if stylus.path == touch.path:
        raise RuntimeError(
            f"Stylus and touch resolved to the same device: {stylus.path}"
        )
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
