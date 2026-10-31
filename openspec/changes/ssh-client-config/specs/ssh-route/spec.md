# Spec Delta

## Purpose

Defines how the connection to a home host is routed (home network, Tailscale, jump host) under one alias, and how the home network is learned instead of configured.

## ADDED Requirements

### Requirement: One alias, routes in order
`ssh-route`, used as `ProxyCommand` with the alias and the routes of a host (`lan=<address:port>`, `ts=<name:port>`, `jump=<jump host:port>`, each optional), SHALL try the given routes in the order lan, ts, jump and SHALL connect over the first that works. When no route works, it SHALL exit with an error that names each route and why it was skipped.

#### Scenario: At home
- **WHEN** a user on the home network runs `ssh homeserver`
- **THEN** the connection goes directly to the LAN address

#### Scenario: Away without Tailscale
- **WHEN** a user outside the home network without a working Tailscale runs `ssh homeserver`
- **THEN** the connection goes through the tunnel port on the jump host

#### Scenario: No route works
- **WHEN** every route fails
- **THEN** ssh fails with a message that lists lan, ts and jump with the reason for each

### Requirement: One host key per alias
Host blocks that use `ssh-route` SHALL set `HostKeyAlias`, so that every route checks the same host key and a wrong host on a route fails host key verification instead of being used.

#### Scenario: Foreign network with the same subnet
- **WHEN** another host answers on the LAN address in a foreign network
- **THEN** the lan route is not used and ssh never connects to that host

### Requirement: Home network is learned
The lan route SHALL be used only on a network known as home. A network SHALL be identified by the hardware address of its default gateway, learned without configuration: on an unknown network, the host key at the LAN address of the target is compared with the known host key of the alias; a match marks the network as home, otherwise as away.

#### Scenario: Replaced home gateway
- **WHEN** the home gateway was replaced and a user at home runs `ssh homeserver`
- **THEN** the host key at the LAN address matches, the new gateway is learned as home and the connection goes directly

#### Scenario: Known away network
- **WHEN** a network was marked as away less than 12 hours ago
- **THEN** the lan route is skipped without a network probe

### Requirement: No network details in configuration or repository
`ssh-route` SHALL NOT need a configured gateway address or network. Learned networks SHALL be stored only in the user's cache on the host.

#### Scenario: Fresh host
- **WHEN** `ssh-route` runs for the first time on a host
- **THEN** it works without any network setting and creates its cache

### Requirement: Newly learned home gateway is reported
When a home gateway is learned while another one is stored, `ssh-route` SHALL record an event without the hardware address and an attention item. The attention item SHALL offer to remove the older entry.

#### Scenario: Second home gateway
- **WHEN** a new home gateway is learned and an older one is stored
- **THEN** `machine attention` shows the item and removing the older entry keeps only the new one

### Requirement: Tailscale is optional
The ts route SHALL be tried only when Tailscale is installed, logged in and reports the peer as online, and only after a short reachability probe. Otherwise it SHALL be skipped without delay.

#### Scenario: Logged out of Tailscale
- **WHEN** Tailscale is installed but logged out
- **THEN** the ts route is skipped and the jump route is tried

#### Scenario: Tailscale reports online but the connection hangs
- **WHEN** the peer is reported online but the probe gets no answer within its timeout
- **THEN** the ts route is skipped and the jump route is tried

### Requirement: Jump route on the jump host itself
When `ssh-route` runs on the jump host of the jump route, it SHALL connect to the tunnel port on the local host directly instead of jumping to itself.

#### Scenario: Shell on Oracle
- **WHEN** a user on Oracle runs `ssh homeserver`
- **THEN** the connection goes to the local tunnel port without a jump

### Requirement: Private context only
`ssh-route` SHALL be available on every host with the `core` group, and host blocks that use it SHALL appear only in the host list of the context `private`.

#### Scenario: Work host
- **WHEN** a work host writes its host list
- **THEN** no host block uses `ssh-route`
