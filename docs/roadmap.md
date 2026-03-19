# Roadmap

## Phase 0 — Foundation ✅

- Procedural river generation with continuous forward scroll.
- Detect collision with river banks and bridges.
- Fuel burn/refuel loop and missile firing.
- Missile lifetime (2 s) and fire cooldown (0.5 s).
- Helicopter enemies patrolling laterally within river bounds; destroy for +10 score.
  - Helicopters spawn in level-sized groups (1 per group at level 1, 2 at level 2, etc.), stacked vertically with random X positions.
  - Helicopter sprite mirrors horizontally to always face direction of travel.
- Tank enemies on river banks firing horizontal missiles every 2 s; destroy for +30 score. Unlocked at level 2.
- Fast jet enemies crossing the full river width horizontally. Unlocked at level 3.
- Enemy spawn density scales +10 % per level for all enemy types.
- Score: fuel station +10, bridge +20, helicopter +10, tank +30.
- Land decorations (trees, bushes, rocks) covering ~20 % of bank area; coverage is a configurable parameter (`land_decoration_coverage` in `game.yaml`).
- Key-state input model (`keydown`/`keyup`) for smooth, latency-free movement.
- Setup web client shell.
- Define shared protocol (input/state messages).
- Implement `keydown`/`keyup` protocol with server-side `keys_down` set per session.
- Implement config-based auth (`/auth/login`) for one dev user.
- Return `501` for `/auth/register`, `/auth/refresh`, `/auth/logout`.
- PostgreSQL persistence for completed game results; top-10 leaderboard via HTTP and demo UI.
- Add backend Docker runtime and local compose config.
- Add unit tests for auth/JWT/WS join/entity/missile/tank behavior.
- Clean Architecture split: `SessionRuntime` (application layer) ↔ `WebSocketGateway` (adapter layer).

## Phase 1 — Full Auth & Profile (Planned)

- `/auth/register`, `/auth/refresh`, `/auth/logout` endpoints.
- Named player profiles with persistent score history.
- Player checkpoint persistence across sessions (`player_checkpoints`).

## Phase 2 — Scale (Planned)

- Multiple service instances behind load balancer.
- Sticky routing by `session_id`.
- Redis for cross-instance presence and pub/sub.
- Replay/seed determinism.
