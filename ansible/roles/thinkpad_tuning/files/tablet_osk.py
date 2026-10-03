#!/usr/bin/env python3
"""Enable GNOME's on-screen keyboard while the ThinkPad is folded into tablet mode.

GNOME only pops the keyboard up after a finger touch; with the a11y switch on it
also appears when a text field is focused by pen.
"""

import select
import subprocess
import sys

TABLET_MODE = "/sys/devices/platform/thinkpad_acpi/hotkey_tablet_mode"


def set_osk(enabled: bool) -> None:
    subprocess.run(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.a11y.applications",
            "screen-keyboard-enabled",
            "true" if enabled else "false",
        ],
        check=False,
    )


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else TABLET_MODE
    with open(path) as switch:
        state = None
        poller = select.poll()
        poller.register(switch, select.POLLPRI | select.POLLERR)
        while True:
            switch.seek(0)
            tablet = switch.read().strip() == "1"
            if tablet != state:
                state = tablet
                set_osk(tablet)
            # sysfs notifies on change; the timeout covers firmware that does not.
            poller.poll(5000)


if __name__ == "__main__":
    main()
