# Roadmap

## Phase 0 — Foundation ✅

- Procedural river generation with continuous forward scroll.
- Detect collision with river banks and bridges.
- Fuel burn/refuel loop and missile firing.
- Missile lifetime (2 s) and fire cooldown (0.5 s).
- Helicopter enemies patrolling laterally within river bounds; destroy for +10 score.
- Tank enemies on river banks firing horizontal missiles every 2 s; destroy for +30 score.
- Key-state input model (`keydown`/`keyup`) for smooth, latency-free movement.
- Setup web client shell.
- Define shared protocol (input/state messages).
- Implement `keydown`/`keyup` protocol with server-side `keys_down` set per session.
- Implement config-based auth (`/auth/login`) for one dev user.
- Return `501` for `/auth/register`, `/auth/refresh`, `/auth/logout`.
- Add backend Docker runtime and local compose config.
- Add unit tests for auth/JWT/WS join/entity/missile/tank behavior.
- Clean Architecture split: `SessionRuntime` (application layer) ↔ `WebSocketGateway` (adapter layer).

## Phase 1 — Persistence & Profile (Planned)

- PostgreSQL integration: `players`, `player_sessions`, `highscores`.
- `/auth/register`, `/auth/refresh`, `/auth/logout` endpoints.
- Leaderboard HTTP endpoint.
- Player checkpoint persistence (`player_checkpoints`).

## Phase 2 — Scale (Planned)

- Multiple service instances behind load balancer.
- Sticky routing by `session_id`.
- Redis for cross-instance presence and pub/sub.
- Replay/seed determinism.
