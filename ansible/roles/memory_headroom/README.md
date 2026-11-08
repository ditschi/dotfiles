---
# Room before an OOM kill: grows the swap file on disk in place to RAM + 2 GiB (never
# shrunk; skipped with a warning on btrfs, a nearly full disk or too little free RAM to
# turn it off, retried on the next run), raises the systemd-oomd memory
# pressure limit of user sessions to 80 % and turns off swap-based systemd-oomd kills.
# The Claude app's scope drop-ins are in the dotfile group memory-headroom.
# Feature: memory-headroom, not applied on a detected Raspberry Pi (hw_pi); the swap
# file is changed only when machine_manage_services (not in containers or CI).
