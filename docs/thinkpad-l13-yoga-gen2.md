# ThinkPad L13 Yoga Gen 2 on Ubuntu

Notes for model 20VK (i5-1135G7, Tiger Lake), plus what sets it up. Apply with `machine apply`.

| What | How it is selected | Role |
| --- | --- | --- |
| S3 suspend, `touchpad-reset`, on-screen keyboard in tablet mode | detected model (DMI `ThinkPad L13 Yoga Gen 2`), no feature | `thinkpad_l13_yoga_gen2` |
| Lid does nothing | feature `lid-switch` (laptops) | `lid_switch` |
| Power profile per power source | feature `power-profile-switch` (laptops) | `power_profile_switch` |
| Battery charge thresholds | feature `battery-charge-limit` (laptops) | `battery_charge_limit` |
| zram swap | feature `zram-swap` | `zram_swap` |
| Touch extensions | feature `touch-device` | `touch_device` |

The laptop features are preselected on every desktop and applied only when Ansible detects a
laptop; any other laptop gets them too. Only the first row is specific to this model.

## Suspend: use S3, not Modern Standby

Symptom: on battery the laptop sometimes could not be woken from sleep; plugging in the
charger woke it at once.

Cause: the BIOS default "Windows 10 and Linux" only offers suspend-to-idle (s2idle). On this
model s2idle resume is unreliable, and the embedded controller reacts to the charger but not
always to the power button or lid.

Fix (manual, once): F1 at boot → Config → Power → **Sleep State = Linux S3**.

The model role adds `mem_sleep_default=deep` through `/etc/default/grub.d/thinkpad-l13-yoga-gen2.cfg` and
warns during apply when the firmware does not offer `deep`.

Check:

```bash
cat /sys/power/mem_sleep                      # s2idle [deep]
journalctl -k | grep "suspend entry"          # (deep)
cat /sys/power/suspend_stats/fail             # 0
```

If these show up after resume from S3 (not seen so far on this machine):

| Problem | Fix |
| --- | --- |
| Touchpad buttons dead | `options psmouse elantech_smbus=0` in `/etc/modprobe.d/psmouse.conf`, then `update-initramfs -u` |
| NVMe I/O errors, root read-only | kernel parameter `nvme_core.default_ps_max_latency_us=0` (reported with the factory Kioxia SSD) |

## Touchpad and TrackPoint freeze

Symptom: touchpad and TrackPoint stop at the same time while the touchscreen and keyboard keep
working (seen on 2026-10-28 after two days of uptime, in laptop mode, with no kernel message).

Cause: both sit on one Elan chip on I2C (`elan_i2c`, address `0-0015`). It hangs and sends no
more interrupts; the input devices stay registered.

Fix: the model role installs `touchpad-reset`, which reloads `elan_i2c` (asks for sudo).

```bash
grep elan_i2c /proc/interrupts      # count does not grow while touching: chip hangs
touchpad-reset
```

Suspend and resume usually resets the chip too.

## Lid

Closing the lid does nothing, on battery, on the charger and when docked
(`/etc/systemd/logind.conf.d/50-lid-switch.conf`). Suspend stays available through the menu
and the power button.

```bash
systemd-analyze cat-config systemd/logind.conf | grep -i lid   # HandleLidSwitch*=ignore
```

## Battery charge thresholds

Default: charging starts below 75 % and stops at 80 % (`battery_charge_limit_start`,
`battery_charge_limit_stop`). This suits a laptop that is mostly on the charger and
sometimes away for a day. The command uses the kernel's generic battery interface, so it also
works on other laptops; a battery that only offers a stop threshold gets just that one.

```bash
battery-charge                 # show level and thresholds
sudo battery-charge full       # charge to 100 % before a trip
sudo battery-charge normal     # back to 75/80 (also happens at every boot)
```

## Power profile

`performance` on the charger, `balanced` on battery, switched by a udev rule on plug and
unplug and at boot. A profile picked by hand in GNOME stays until the next plug event.
A profile the host does not offer is skipped. Variables: `power_profile_switch_ac`,
`power_profile_switch_battery`.

## zram swap

Compressed swap in RAM (half of RAM, at most 8 GiB, zstd), used before the swap file on
disk. Variable: `zram_swap_size`. Not applied on Raspberry Pis.

```bash
swapon --show
zramctl
```

## Tablet mode

- Keyboard and touchpad lock when folded (kernel, nothing to configure).
- **On-screen keyboard**: the user service `tablet-osk` turns GNOME's on-screen keyboard on
  while folded and off again in laptop mode. It then opens whenever a text field gets focus,
  by finger or pen. Chromium and Electron apps only report text fields when started with
  `--enable-wayland-ime`.
  Status: `systemctl --user status tablet-osk`.
- **Rotation**: automatic through `iio-sensor-proxy`.

### Touch extensions (feature `touch-device`)

Installed for the login user by role `touch_device`:

- **TouchUp**: touch tweaks for GNOME Shell. On the on-screen keyboard it adds key popups,
  extended keys, swipe down to close, a paste button and layout switching by swiping the
  space bar. Its other touch features are switched on and off in Extension Manager → TouchUp
  → Settings.
- **Screen Rotate**: a rotate button in the quick settings for turning the screen by hand,
  also in laptop mode.

A new extension is only loaded at the next login. After logging in again, run
`machine apply` once more, or switch the extensions on in Extension Manager.

Not installed: *GJS OSK* (a separate, more compact keyboard with Ctrl, Alt and arrows). It
replaces the built-in keyboard, so TouchUp's keyboard features would not apply to it.

## Pen

- Palm rejection: feature `stylus-touch-guard`.
- Buttons: Settings → Wacom Tablet → Stylus. Hold the pen near the screen so it is listed,
  then assign each button (right click, middle click, back, forward) and set the tip
  pressure curve. In Xournal++ the buttons can be mapped per tool under
  Edit → Preferences → Stylus (for example lower button = eraser, upper button = select).

## Video decoding

Firefox (snap) uses VA-API hardware decoding on the Iris Xe GPU by default; no settings
needed. The video decoder process has the Intel `iHD` driver loaded.

```bash
vainfo                         # host driver and supported codecs
```

In Firefox, `about:support` → Media lists the codecs with hardware decoding.

## Battery metrics

`machine/laptop` Telegraf config reports measurement `battery`: `status` (Charging,
Discharging, Full, Not charging), `capacity_percent`, `power_w`, `energy_wh`,
`energy_full_wh`, `energy_full_design_wh`, `voltage_v`, `cycle_count`, `charge_stop_percent`.

## Not done, on purpose

- Fan control: this EC does not accept fan writes through `thinkpad_acpi`; tools that write
  EC registers directly are risky for little gain.
- `acpi.ec_no_wakeup` and disabling ACPI wake sources: only relevant for s2idle.
- Hibernate: needs swap of at least RAM size; S3 made it unnecessary.

## Sources

- [Debian wiki: L13 Yoga Gen 2](https://wiki.debian.org/InstallingDebianOn/Thinkpad/L13%20Yoga%20Gen%202/Bookworm)
- [Arch forum: L13 Yoga wakes when closing the lid](https://bbs.archlinux.org/viewtopic.php?id=280925)
- [ArchWiki: Laptop/Lenovo](https://wiki.archlinux.org/title/Laptop/Lenovo)
