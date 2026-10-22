# Backlog

Ideas that are not yet planned. Each entry becomes an OpenSpec change (`/opsx-propose`) when picked up. Nothing here is decided.

## Automatic VPN on work machines outside the corporate network

Idea from the owner: on work machines, detect which network the machine is on. When it is not the corporate network (not onsite, for example at home or on a travel or hotspot connection), start the VPN automatically.

Wanted scope:
- Network types: LAN, Wi-Fi and USB network (for example USB tethering).
- Profiles: work-machine only.

Open questions (to ask when this is picked up):
- How to recognise the corporate network reliably (DNS suffix, reachable internal host, gateway, SSID).
- Which VPN client and how it is started without root, since work machines may not allow Ansible to become root.
- What triggers the check (network change event, shell start, timer) and how to avoid flapping between networks.
- Whether the user can pause or override the automatic start.
