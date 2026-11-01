# Fingerprint login on Ubuntu

Manual setup, once per host with a sensor. `machine` and Ansible do not manage it: Ubuntu
26.04 already ships `fprintd` and `libpam-fprintd`, and enrolling needs the finger on the
sensor anyway.

Tested on the ThinkPad L13 Yoga Gen 2 (Synaptics `06cb:00bd`, match-on-chip).

## Check the sensor

```bash
fprintd-list $USER
```

`found 1 devices` means the sensor works. `No devices available` means libfprint does not
support it.

## Enroll fingers

```bash
fprintd-enroll -f right-index-finger
fprintd-enroll -f left-index-finger
fprintd-list $USER
fprintd-verify -f right-index-finger
```

Finger names: `{left,right}-{thumb,index-finger,middle-finger,ring-finger,little-finger}`.
GNOME Settings → Users → Fingerprint Login does the same.

Synaptics chips store the prints on the chip (15 slots). If enrolling fails because the chip
is full, old prints from another OS are still on it.

## Login and lock screen

Nothing to configure: GDM runs `gdm-fingerprint` next to `gdm-password`, so finger and
password work at the same time.

A fingerprint login after boot leaves the GNOME keyring locked; it asks for the password
later. Log in with the password after boot and use the finger on the lock screen.

## sudo (optional, toggle)

`pam_fprintd` in `common-auth` asks for the finger first and for the password only after the
timeout (PAM is sequential). Ubuntu's profile `fprintd` waits 10 s; a local profile with 6 s:

```bash
sudo tee /usr/share/pam-configs/fprintd-6s >/dev/null <<'EOF'
Name: Fingerprint authentication (6s timeout)
Default: no
Priority: 260
Conflicts: fprintd
Auth-Type: Primary
Auth:
	[success=end default=ignore]	pam_fprintd.so max-tries=1 timeout=6
EOF
```

On and off:

```bash
sudo pam-auth-update --enable fprintd-6s
sudo pam-auth-update --disable fprintd-6s
```

Test in a new terminal and keep the old one open: `sudo -k; sudo true`.

Through `common-auth` this also applies to `su`, TTY login and polkit dialogs. Over SSH, sudo
also waits for the finger first (`pam_fprintd` does not detect remote sessions).
