"""Device resolution of stylus_touch_guard.py against fake evdev devices."""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass, field

import pytest

from package_sets import ANSIBLE

SCRIPT = ANSIBLE / "roles/stylus_touch_guard/files/stylus_touch_guard.py"

# Values from linux/input-event-codes.h.
EV_KEY, EV_ABS = 0x01, 0x03
BTN_TOOL_PEN, BTN_TOOL_FINGER, BTN_TOUCH = 0x140, 0x145, 0x14A
ABS_X, ABS_MT_POSITION_X = 0x00, 0x35
INPUT_PROP_POINTER, INPUT_PROP_DIRECT = 0x00, 0x01


@dataclass
class FakeDevice:
    name: str
    path: str
    keys: list[int] = field(default_factory=list)
    absolute: list[int] = field(default_factory=list)
    props: list[int] = field(default_factory=list)
    readable: bool = True

    def capabilities(self, absinfo: bool = True):
        if not self.readable:
            raise OSError("permission denied")
        return {EV_KEY: self.keys, EV_ABS: self.absolute}

    def input_props(self):
        if not self.readable:
            raise OSError("permission denied")
        return self.props


PEN = dict(keys=[BTN_TOOL_PEN, BTN_TOUCH], absolute=[ABS_X], props=[INPUT_PROP_DIRECT])
SCREEN = dict(
    keys=[BTN_TOOL_FINGER, BTN_TOUCH],
    absolute=[ABS_X, ABS_MT_POSITION_X],
    props=[INPUT_PROP_DIRECT],
)
TOUCHPAD = dict(
    keys=[BTN_TOOL_FINGER, BTN_TOUCH],
    absolute=[ABS_X, ABS_MT_POSITION_X],
    props=[INPUT_PROP_POINTER],
)

# The ThinkPad L13 Yoga Gen 2, Finger listed before Pen as on the real host.
L13_YOGA = [
    FakeDevice("Wacom Pen and multitouch sensor Finger", "/dev/input/event8", **SCREEN),
    FakeDevice("Wacom Pen and multitouch sensor Pen", "/dev/input/event9", **PEN),
    FakeDevice("Elan Touchpad", "/dev/input/event5", **TOUCHPAD),
    FakeDevice("Elan TrackPoint", "/dev/input/event6", keys=[0x110]),
]


@pytest.fixture
def guard(monkeypatch):
    devices: dict[str, FakeDevice] = {}

    def input_device(path):
        return devices[path]

    ecodes = types.SimpleNamespace(
        EV_KEY=EV_KEY,
        EV_ABS=EV_ABS,
        BTN_TOOL_PEN=BTN_TOOL_PEN,
        ABS_MT_POSITION_X=ABS_MT_POSITION_X,
        INPUT_PROP_POINTER=INPUT_PROP_POINTER,
        INPUT_PROP_DIRECT=INPUT_PROP_DIRECT,
    )
    evdev = types.SimpleNamespace(
        InputDevice=input_device, ecodes=ecodes, list_devices=lambda: list(devices)
    )
    monkeypatch.setitem(sys.modules, "evdev", evdev)
    monkeypatch.setitem(sys.modules, "psutil", types.SimpleNamespace())
    spec = importlib.util.spec_from_file_location("stylus_touch_guard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def use(*devs: FakeDevice):
        devices.clear()
        devices.update({d.path: d for d in devs})
        return module

    return use


def test_l13_yoga_resolves_pen_and_finger(guard):
    module = guard(*L13_YOGA)
    stylus, touch_path = module.resolve_devices()
    assert stylus.name == "Wacom Pen and multitouch sensor Pen"
    assert touch_path == "/dev/input/event8"


def test_l13_yoga_by_name_when_capabilities_are_unreadable(guard):
    devices = [FakeDevice(d.name, d.path, readable=False) for d in L13_YOGA]
    stylus, touch_path = guard(*devices).resolve_devices()
    assert stylus.path == "/dev/input/event9"
    assert touch_path == "/dev/input/event8"


def test_stylus_found_by_capability_despite_name(guard):
    module = guard(FakeDevice("Some Digitizer", "/dev/input/event3", **PEN))
    assert module.is_stylus(module.find_device(module.is_stylus))


def test_touchpad_is_never_the_touch_device(guard):
    pen = FakeDevice("Wacom Pen and multitouch sensor Pen", "/dev/input/event9", **PEN)
    touchpad = FakeDevice("Elan Touchpad", "/dev/input/event5", **TOUCHPAD)
    unnamed_pad = FakeDevice("SYNA1234:00 06CB:CE2D", "/dev/input/event4", **TOUCHPAD)
    module = guard(pen, touchpad, unnamed_pad)
    assert module.find_device(module.is_touchscreen) is None
    with pytest.raises(RuntimeError, match="Could not find"):
        module.resolve_devices()


def test_touchpad_by_name_is_excluded_without_capabilities(guard):
    module = guard(FakeDevice("Elan Touchpad", "/dev/input/event5", readable=False))
    assert not module.is_touchscreen(module.find_device(lambda _: True))
    assert not module.is_stylus(module.find_device(lambda _: True))


def test_non_wacom_touchscreen_by_capability(guard):
    pen = FakeDevice("Wacom Pen and multitouch sensor Pen", "/dev/input/event9", **PEN)
    screen = FakeDevice("ELAN9008:00 04F3:2C82", "/dev/input/event7", **SCREEN)
    touchpad = FakeDevice("Elan Touchpad", "/dev/input/event5", **TOUCHPAD)
    _, touch_path = guard(touchpad, screen, pen).resolve_devices()
    assert touch_path == "/dev/input/event7"
