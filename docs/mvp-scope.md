# MVP Scope

## MVP Goal

Deliver a playable single-player prototype where the player can:

1. Spawn at a last visited bridge.
2. Fly to next bridge
3. Destroy enemies

## Included in MVP

### Gameplay

- 2D top-down plane movement (slow/fast, left/right).
- basic gun to shot destroy enemy objects
- Refuel at stations.

### Phase 0 Platform Foundation

- Config-based login for one dev user.
- JWT issuance on login and token validation on WebSocket join.
- Backend runs in a Docker container.
- Unit tests are required and run in CI gate.
