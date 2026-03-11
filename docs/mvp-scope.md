# MVP Scope

## MVP Goal

Deliver a playable single-player prototype where the player can:

1. Login with configured dev credentials.
2. Join authoritative WebSocket session.
3. Fly through procedurally generated river segments.
4. Avoid river bank and bridge collisions.
5. Refuel from fuel stations and fire missiles.

## Included in MVP

### Gameplay

- 2D top-down plane movement (left/right input).
- Continuous camera scroll and periodic snapshots.
- Fuel burn over time and refuel at stations.
- Missile firing and collision-based score gain.
- Bridge spawning and bridge collision damage.
- Game over + restart command flow.

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
