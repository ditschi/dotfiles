# Spec Delta

## Purpose

Brings the work laptop into the work network automatically while the owner is logged
in: it detects whether the work network is reachable and starts or restores the VPN
when it is not.

## ADDED Requirements

### Requirement: Runs only in the owner's desktop session
The VPN watcher SHALL run only while the owner is logged in to a graphical session on a work-context desktop host that has the OSD VPN tool (`/usr/bin/osd-vpn-connect`). It SHALL start with that session and stop when the session ends; ending the session SHALL NOT disconnect the VPN. Private hosts, servers and containers SHALL NOT get the watcher.

#### Scenario: Owner logs in
- **WHEN** the owner logs in to the desktop on the work laptop
- **THEN** the watcher starts and checks the network immediately

#### Scenario: Owner logs out
- **WHEN** the owner logs out while the VPN is connected
- **THEN** the watcher stops and the VPN stays connected

#### Scenario: Nobody logged in
- **WHEN** the work laptop is on but the owner has no graphical session
- **THEN** the watcher does not run and no VPN connect is started on the owner's behalf

#### Scenario: Host without the OSD VPN tool
- **WHEN** a work host has no `/usr/bin/osd-vpn-connect`
- **THEN** the watcher is not enabled

### Requirement: Checks on network events
The watcher SHALL check the network state at session start, after waking from sleep, after every network connectivity change reported by NetworkManager, and at least every 2 minutes as a fallback. Events that arrive close together SHALL lead to a single check.

#### Scenario: Wake from sleep
- **WHEN** the laptop wakes from sleep
- **THEN** the watcher checks the network within seconds, without waiting for the periodic check

#### Scenario: Burst of network events
- **WHEN** NetworkManager reports several changes within a few seconds
- **THEN** the watcher runs one check after the changes have settled

### Requirement: Work network detection
The host SHALL count as in the work network when the Kerberos KDC of the default realm is reachable on TCP port 88. In the work network the watcher SHALL NOT start the VPN, whether the connection is office LAN, USB-LAN, work Wi-Fi or an existing VPN.

#### Scenario: Office network
- **WHEN** the laptop is connected to the office LAN and the KDC is reachable
- **THEN** no VPN connect is started

#### Scenario: Home network
- **WHEN** the laptop has a network connection but the KDC is not reachable and no VPN client is running
- **THEN** the watcher starts the VPN

#### Scenario: No network
- **WHEN** NetworkManager reports no network connection
- **THEN** the watcher does not try to connect and waits for the next event

### Requirement: Prefer the VPN client's own reconnect
When the KDC is not reachable but the VPN client is still running or a VPN connect is in progress, the watcher SHALL wait up to 45 seconds after the triggering event for the connection to recover by itself before it starts a new connect.

#### Scenario: Short sleep
- **WHEN** the laptop wakes from a short sleep and the VPN client reconnects within the grace period
- **THEN** the watcher does not start a new connect

#### Scenario: Reconnect does not succeed
- **WHEN** the KDC is still not reachable 45 seconds after the event
- **THEN** the watcher starts a new VPN connect

#### Scenario: Client gives up early
- **WHEN** the VPN client ends its own reconnect attempt before the 45 seconds are over
- **THEN** the watcher starts a new connect within about 5 seconds

### Requirement: Non-interactive VPN connect
The watcher SHALL connect the VPN without any prompt, using the password from `get-password` for the VPN authentication and not a password copy stored by the VPN tool, also when the GNOME keyring is locked. A certificate expiry warning of the VPN tool SHALL NOT block the connect. After a successful connect the Kerberos ticket SHALL be valid.

#### Scenario: Locked keyring
- **WHEN** the keyring is locked and the env files hold the owner's password
- **THEN** the VPN connects with that password and no prompt or dialog appears

#### Scenario: Stale copy in the VPN tool
- **WHEN** the VPN tool still stores the old password after a password change and the env files hold the new one
- **THEN** the VPN authenticates with the new password from the env files

#### Scenario: Ticket after connect
- **WHEN** a VPN connect by the watcher succeeds
- **THEN** `klist -s` succeeds afterwards

### Requirement: Failure guard applies to VPN connects
VPN connects by the watcher SHALL be subject to the authentication failure guard of the `kerberos-tokens` capability: a rejected password SHALL count as a failure, a missing network or an unreachable gateway SHALL NOT. While the guard is stopped the watcher SHALL NOT start a VPN connect.

#### Scenario: Rejected password
- **WHEN** the VPN gateway rejects the password
- **THEN** the guard counts one failure

#### Scenario: Gateway not reachable
- **WHEN** the VPN connect fails because the gateway cannot be reached
- **THEN** no failure is counted and the watcher retries on the next event

#### Scenario: Guard stopped
- **WHEN** the guard has stopped automatic attempts
- **THEN** the watcher does not start a VPN connect until the guard is reset

### Requirement: Manual disconnect pauses the watcher
When the owner disconnects the VPN with `osd-vpn-disconnect` in a work shell, the watcher SHALL NOT start a VPN connect until the owner logs in again, the laptop wakes from sleep, or the owner connects by hand with `vpn-pw`.

#### Scenario: Manual disconnect
- **WHEN** the owner runs `osd-vpn-disconnect` and the network stays up
- **THEN** the watcher does not reconnect the VPN

#### Scenario: Wake after a manual disconnect
- **WHEN** the laptop wakes from sleep after a manual disconnect
- **THEN** the watcher checks the network and connects the VPN when needed

#### Scenario: VPN drops by itself
- **WHEN** the VPN connection ends without a manual disconnect
- **THEN** the watcher reconnects as usual

### Requirement: Certificate expiry notice
When the VPN machine certificate expires within 20 days, the watcher SHALL show a desktop notification at most once per day that names the days left and the renewal command `osd-wifivpn-enroll`.

#### Scenario: Certificate close to expiry
- **WHEN** the certificate expires in 12 days and no notice was shown today
- **THEN** a notification with "12 days" and `osd-wifivpn-enroll` is shown

#### Scenario: Certificate valid long enough
- **WHEN** the certificate is valid for more than 20 days
- **THEN** no notification is shown

### Requirement: Bounded VPN connect
A VPN connect started by the watcher SHALL be stopped after 120 seconds, logged and retried on the next event; a stopped connect SHALL NOT count as a failure for the guard. When the watcher's event source ends, the watcher SHALL restart it.

#### Scenario: Hanging connect
- **WHEN** the VPN connect script has not finished after 120 seconds
- **THEN** it is stopped, the timeout is logged and the watcher keeps reacting to events

#### Scenario: Tunnel up before the script ends
- **WHEN** the watcher's connect has brought the tunnel up and the KDC is reachable, but the script still waits for its own network check
- **THEN** the connect counts as successful at once, no timeout is logged, and the script finishes in the background

#### Scenario: Event source ends
- **WHEN** the D-Bus monitor process exits
- **THEN** the watcher starts it again

### Requirement: VPN diagnostics
The output of the VPN connect script SHALL be written line by line to the `work-net` log file, without the password. `work-net status` SHALL also show whether the VPN client runs, whether the watcher is paused and the certificate's days left. `work-net vpn check --dry-run` SHALL print what the watcher would do now and why, without doing it.

#### Scenario: Reading a failed connect
- **WHEN** an automatic connect failed
- **THEN** `~/.local/state/work-net/work-net.log` shows the script's messages for that attempt

#### Scenario: Dry run
- **WHEN** the owner runs `work-net vpn check --dry-run` at home with no VPN client running
- **THEN** it prints that it would connect, with the reason, and no connect is started
