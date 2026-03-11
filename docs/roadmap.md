# Roadmap

## Phase 0 — Foundation

- Generate 1 Level
- No enemy, just fly to next bridge
- Detect collision with river bank, respawn at the bridge if crash
- Setup web client shell.
- Define shared protocol (input/state messages).
- Implement config-based auth (`/auth/login`) for one dev user.
- Return `501` for `/auth/register`, `/auth/refresh`, `/auth/logout`.
- Add backend Docker runtime and local compose config.
- Add unit tests for auth/JWT/WS join behavior.
