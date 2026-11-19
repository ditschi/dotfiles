# ssh-tunnel Specification

## Purpose
Defines the reverse SSH tunnels from home hosts and devices to the jump host that carry the jump route of `ssh-route`: the restricted tunnel user on the jump host, the client on hosts with dotfiles and the script for devices without dotfiles.

## Requirements

### Requirement: Restricted tunnel user on the jump host
On a host with the feature `jump-host`, a system user `tunnel` SHALL exist without a login shell. sshd SHALL allow this user remote port forwarding only: no shell, command, TTY, local forwarding, agent, X11 or stream-local forwarding.

#### Scenario: Login attempt with a tunnel key
- **WHEN** a device runs `ssh tunnel@oracle` with its tunnel key and asks for a shell
- **THEN** no shell or command runs and the session gets no TTY

#### Scenario: Local forward attempt
- **WHEN** a device with a tunnel key asks for `-L` or `-W` to any address
- **THEN** sshd refuses the forward

### Requirement: One key line per tunnel from the host list
The `authorized_keys` of `tunnel` SHALL hold one line per host block in the host list whose jump route names this host, each `restrict,port-forwarding,permitlisten="127.0.0.1:<port>"` with the port of that route and the device's key: `machine/ssh_tunnel_keys/<alias>.pub`, else `machine/ssh_keys/<alias>.pub`.

#### Scenario: homeserver
- **WHEN** the host list routes homeserver with `jump=oracle:2223` and `jump-host` is applied on oracle
- **THEN** the key of `machine/ssh_keys/homeserver.pub` may listen only on `127.0.0.1:2223`

#### Scenario: Device without dotfiles
- **WHEN** the host list routes offsite-nas with `jump=oracle:2230` and `machine/ssh_tunnel_keys/offsite-nas.pub` exists
- **THEN** that key may listen only on `127.0.0.1:2230`

### Requirement: Tunnel keys managed as a whole
The role SHALL write the whole `authorized_keys` of `tunnel`, so lines added by hand and devices no longer in the host list are removed. A tunnel without a key file SHALL be skipped with a warning that names the missing file.

#### Scenario: Device removed from the host list
- **WHEN** a host block with a jump route to oracle is removed and `jump-host` is applied again
- **THEN** its key line is gone

#### Scenario: Key file missing
- **WHEN** a jump route names a device that has no key file
- **THEN** the other lines are written and the run warns about the missing file

### Requirement: Tunnel list from the written host list
The jump host SHALL read the tunnels from the host list file already written on the host, never from Bitwarden. Without that file, the role SHALL leave the existing `authorized_keys` of `tunnel` unchanged and warn.

#### Scenario: Background update on oracle
- **WHEN** the background update applies `jump-host`
- **THEN** it uses the existing host list file and does not ask for Bitwarden

#### Scenario: No host list on the host
- **WHEN** the host list file is missing
- **THEN** the tunnel keys stay as they are and the run warns

### Requirement: Loopback-only listeners
Tunnel ports on the jump host SHALL listen only on the loopback address, and `GatewayPorts` SHALL be off for `tunnel`. Applying `jump-host` SHALL NOT open firewall ports.

#### Scenario: Port scan from the internet
- **WHEN** someone connects to oracle's public address on port 2223
- **THEN** the connection is refused or dropped

### Requirement: Dead tunnel sessions end on the jump host
sshd SHALL end a `tunnel` session that stops answering within about two minutes, so that a reconnecting device can listen on its port again.

#### Scenario: Device loses its network
- **WHEN** a device's connection breaks without a clean close
- **THEN** its port on oracle is free again within about two minutes

### Requirement: Client tunnel on hosts with dotfiles
On a host with the feature `ssh-tunnel`, a systemd user unit SHALL keep the reverse tunnel open as `tunnel@<jump host>`, forwarding `127.0.0.1:<port>` on the jump host to the host's own SSH port 22. It SHALL start at boot without a login and SHALL restart after every exit, including exit status 0.

#### Scenario: Reboot
- **WHEN** homeserver boots and nobody logs in
- **THEN** port 2223 on oracle reaches homeserver's sshd within a few minutes

#### Scenario: Jump host restarts
- **WHEN** oracle restarts sshd or reboots
- **THEN** the unit reconnects without manual action

### Requirement: Client port from the host's own block
The client SHALL take the jump host and port from the jump route of the host list block whose host key alias is the host's short hostname. Without such a block or route, it SHALL stop with a message naming the host list and SHALL NOT retry until restarted.

#### Scenario: Host not in the host list
- **WHEN** `ssh-tunnel` runs on a host without a block with a jump route
- **THEN** the unit fails once with a hint to add the jump route with `machine ssh add` or `machine ssh edit`

### Requirement: Tunnel connection is never shared
The tunnel connection SHALL NOT use or create a connection-sharing master, and SHALL exit when the jump host refuses the forward, so the restart can try again.

#### Scenario: Shared defaults set ControlMaster
- **WHEN** the base SSH config sets `ControlMaster auto` and `ControlPersist`
- **THEN** the tunnel stays in the foreground and the forward is open as long as it runs

#### Scenario: Port still held by an old session
- **WHEN** the port on the jump host is still taken
- **THEN** the tunnel exits and the next attempt follows after the restart delay

### Requirement: Tunnel script for devices without dotfiles
The repository SHALL provide a tunnel script for devices without dotfiles that runs with BusyBox `sh` and OpenSSH 7.4, uses its own key, checks the jump host against a pinned host key and reads jump host, port and key paths from a local file on the device. Running it again while a tunnel runs SHALL NOT start a second one.

#### Scenario: Boot task and watchdog
- **WHEN** the device's boot task and its periodic watchdog both run the script
- **THEN** exactly one tunnel runs, and the watchdog restarts it after it died

#### Scenario: Jump host key changed
- **WHEN** the jump host presents a key other than the pinned one
- **THEN** the script does not connect and logs the host key failure

### Requirement: Device tunnel keys never grant login
Keys in `machine/ssh_tunnel_keys/` SHALL be used only for the `tunnel` user and SHALL NOT be installed by `sshd_home` or offered for `ssh_allow_from`.

#### Scenario: Setup offers ssh_allow_from
- **WHEN** `machine setup` offers hosts for `ssh_allow_from`
- **THEN** a device with a key only in `machine/ssh_tunnel_keys/` is not offered

### Requirement: Private hosts only
The features `jump-host` and `ssh-tunnel` SHALL be optional on private servers and desktops and excluded for work and in containers.

#### Scenario: Work host
- **WHEN** setup lists the features on a work host
- **THEN** neither `jump-host` nor `ssh-tunnel` is offered
