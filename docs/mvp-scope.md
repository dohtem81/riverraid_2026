# MVP Scope

## MVP Goal

Deliver a playable single-player prototype where the player can:

1. Login with configured dev credentials.
2. Join authoritative WebSocket session.
3. Fly through procedurally generated river segments.
4. Avoid river bank, bridge, and helicopter collisions.
5. Dodge tank missiles fired from the banks.
6. Refuel from fuel stations and fire missiles.
7. Destroy helicopters, tanks, and bridges for score.

## Included in MVP

### Gameplay

- 2D top-down plane movement (key-state left/right input — smooth continuous movement).
- Continuous camera scroll and periodic snapshots.
- Fuel burn over time and refuel at stations.
- Missile firing with lifetime (2 s) and cooldown (0.5 s per shot).
- Collision-based score gain (fuel station +10, bridge +20, helicopter +10, tank +30).
- Bridge spawning and bridge collision damage.
- Helicopter enemies patrolling laterally within river bounds.
- Tank enemies on river banks that shoot horizontal missiles every 2 s.
- Game over + restart command flow.

### Input Model

- `keydown`/`keyup` messages for smooth, continuous movement (no OS key-repeat delay).
- `Space` keydown fires a missile (rate-limited by cooldown).
- Legacy `input` message also accepted for compatibility.

### Phase 0 Platform Foundation

- Config-based login for one dev user.
- JWT issuance on login and token validation on WebSocket join.
- Backend runs in a Docker container.
- Unit tests are required and run in CI gate.

## Not Yet Implemented

- Persistent profile/highscore storage.
- Registration, refresh, and logout flows.
- Multi-player or shared-world sessions.
- Dedicated cache/login service.
