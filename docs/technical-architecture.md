# Technical Architecture (v1)

## Current Implementation Snapshot (March 2026)

- Runtime is a single FastAPI service.
- Auth is name-based with JWT issuance/validation.
- Realtime gameplay is split across two Clean Architecture layers:
  - **`SessionRuntime`** (application layer): owns all game-tick orchestration — world generation, entity advancement, collision resolution, key-state movement, missile/tank logic.
  - **`WebSocketGateway`** (interface adapter): thin transport delegate — decodes/validates WS messages, calls `SessionRuntime`, encodes responses.
- Input uses a key-state model (`keydown`/`keyup`): the server holds a `keys_down` set per session and applies continuous movement each tick without OS key-repeat delay.
- PostgreSQL is integrated for completed game-result persistence and top-score queries.

## High-Level

- **Client:** Browser-based 2D renderer (Canvas/WebGL) with input capture and prediction.
- **Server:** Python async backend with authoritative fixed-tick simulation.
- **Transport:** HTTP for auth/profile/bootstrap, WebSocket for realtime gameplay.
- **Data:** PostgreSQL for durable data; Redis optional for cache/presence/rate-limits.

## Recommended Architecture Shape

For MVP, use a **modular monolith**:

1. Auth/Profile HTTP module
2. WebSocket gateway module
3. Game session runtime module
4. Persistence module

Why this shape:
- Simpler operations and faster iteration than microservices.
- Clear internal boundaries without distributed-system overhead.
- Easy migration path to multi-instance scaling later.

## Clean Architecture Rules (Mandatory from Phase 0)

Dependency direction is strictly inward:

1. Domain
2. Application
3. Interface Adapters
4. Infrastructure/Frameworks

Rules:
- Domain has no dependency on frameworks, transport, databases, env/config loaders, or web libraries.
- Application depends only on Domain abstractions and use-case ports.
- Interface Adapters translate external formats (HTTP/WS/config/DB rows) into Application inputs/outputs.
- Infrastructure provides concrete implementations of ports declared by Application.
- No outward layer may be imported by an inward layer.

Layer responsibilities:
- Domain: game rules, scoring/fuel/collision policies, auth invariants, value objects/entities.
- Application: use cases (`LoginWithConfig`, `ValidateJoinToken`, `ProcessInputTick`, `EmitSnapshot`), transaction boundaries, orchestration.
- Interface Adapters: FastAPI handlers, WebSocket message mappers, config repository adapter, presenter/DTO mapping.
- Infrastructure: FastAPI/Uvicorn bootstrapping, JWT library wiring, config file/env parsing, optional DB/Redis adapters.

Phase 0 constraints under Clean Architecture:
- Auth is name-only; the backend deterministically derives a stable `player_id` from the supplied player name.
- JWT `sub` equals the derived stable `player_id`.
- `POST /auth/register`, `POST /auth/refresh`, `POST /auth/logout` return `501`.
- Runtime is container-first and can run with a colocated PostgreSQL service.
- Unit tests are mandatory and must pass in CI before container publish.

Architecture fitness checks:
- Enforce import boundaries in CI.
- Block PRs where Domain/Application imports framework or infrastructure packages.
- Require new external integrations to be added as adapter implementations behind ports.

## Authoritative Simulation Model

- Tick rate: **30 TPS** (fixed timestep).
- Snapshot broadcast: **~10 Hz** (plus immediate snapshots after accepted input events).
- Client sends **key-state commands** (`keydown`/`keyup`) or legacy `input` commands.
- Server maintains a `keys_down` set per session; movement is applied continuously each tick at `step_x / tick_interval_seconds` game-units/s.
- Server applies validated inputs at tick boundaries and returns snapshots with `last_processed_input_seq` for reconciliation.
- Player missiles: travel upward at `missile_speed`; lifetime `2 s`; cooldown `0.5 s`.
- Tank missiles: travel horizontally at `tank_missile_speed_x`; fired every `2 s` per tank; pruned on world-edge exit.

## Backend Responsibilities

- Verify JWT and map subject to existing `players.id`.
- Bind the connection to an in-memory `session_id`.
- Validate input schema/rates and reject invalid commands.
- Resolve movement, collision, combat, scoring, fuel consumption/refuel.
- Emit event + snapshot messages for the client HUD/render loop.

## Data Ownership

- **Authoritative runtime state:** in-memory inside session runtime.
- **Durable state:** PostgreSQL `game_results` table for completed runs and leaderboard queries.
- **Future durable state:** optional `players`, `player_sessions`, `player_checkpoints`.
- **Cache/transient state:** Redis optional; never authoritative for simulation.

## Security and Fairness

- Server-authoritative movement/combat/fuel and score.
- Input rate-limiting and payload size limits.
- Clamp impossible control transitions and fire rate.
- Short-lived access token + refresh token rotation/revocation.

## Suggested Stack

- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy async + `asyncpg`
- PostgreSQL 15+
- Redis (optional, planned)

## Deployment Plan

### Phase 1 (MVP)

- Single container image.
- One service instance.
- PostgreSQL dependency for leaderboard / finished-game persistence.
- Render deployment should provide `DATABASE_URL` and `JWT_SECRET` via secret environment variables.

Gameplay mode for MVP:
- One active player per game session.
- No shared world state between players.
- Leaderboard is persisted via PostgreSQL.

## Production Configuration

- `APP_ENV=prod` disables insecure defaults and requires explicit `JWT_SECRET` and `DATABASE_URL`.
- Render-style URLs (`postgres://...`, `postgresql://...`) are normalized to `postgresql+asyncpg://...` during startup.
- Secrets must be injected through environment variables, never committed to source.

### Phase 2 (Scale)

- Multiple service instances behind load balancer.
- Sticky routing (or allocator) by `session_id`.
- Redis for cross-instance presence and control signaling.
- Keep each game session single-writer on one instance.

## Non-Goals for MVP

- No microservice split of auth/cache/game runtime.
- No cross-region consistency.
- No UDP transport.

