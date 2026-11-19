## ADDED Requirements

### Requirement: Free tunnel port suggested
When `machine ssh add` asks for the tunnel port of a jump route, it SHALL suggest as default the lowest port from 2223 that no jump route to the same jump host in the host list uses yet.

#### Scenario: Ports 2223 to 2225 taken
- **WHEN** the host list has jump routes to oracle on 2223, 2224 and 2225 and a user adds a home host with the jump host oracle
- **THEN** the tunnel port prompt defaults to 2226

#### Scenario: Gap in the ports
- **WHEN** the host list has jump routes to oracle only on 2223 and 2225
- **THEN** the tunnel port prompt defaults to 2224
