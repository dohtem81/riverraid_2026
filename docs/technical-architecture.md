# Technical Architecture (v1)

## Current Implementation Snapshot (March 2026)

- Runtime is a single FastAPI service.
- Auth is config-based (single configured dev user) with JWT issuance/validation.
- Realtime gameplay runs in-process in the WebSocket gateway and game session service.
- No PostgreSQL or Redis integration is implemented yet.

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
- Auth source is config-file based (single configured user).
- JWT `sub` equals configured stable `player_id`.
- `POST /auth/register`, `POST /auth/refresh`, `POST /auth/logout` return `501`.
- Runtime is container-first (single service container, no DB required).
- Unit tests are mandatory and must pass in CI before container publish.

Architecture fitness checks:
- Enforce import boundaries in CI.
- Block PRs where Domain/Application imports framework or infrastructure packages.
- Require new external integrations to be added as adapter implementations behind ports.

## Authoritative Simulation Model

- Tick rate: **30 TPS** (fixed timestep).
- Snapshot broadcast: **~10 Hz** (plus immediate snapshots after accepted input events).
- Client sends **input-only commands** (`turn`, `fast`, `fire`) with increasing `input_seq`.
- Server applies validated inputs at tick boundaries and returns snapshots with `last_processed_input_seq` for reconciliation.

## Backend Responsibilities

- Verify JWT and map subject to existing `players.id`.
- Bind the connection to an in-memory `session_id`.
- Validate input schema/rates and reject invalid commands.
- Resolve movement, collision, combat, scoring, fuel consumption/refuel.
- Emit event + snapshot messages for the client HUD/render loop.

## Data Ownership

- **Authoritative runtime state:** in-memory inside session runtime.
- **Durable state (planned):** PostgreSQL (`players`, `player_sessions`, `highscores`, optional `player_checkpoints`).
- **Cache/transient state (planned):** Redis optional; never authoritative for simulation.

## Security and Fairness

- Server-authoritative movement/combat/fuel and score.
- Input rate-limiting and payload size limits.
- Clamp impossible control transitions and fire rate.
- Short-lived access token + refresh token rotation/revocation.

## Suggested Stack

- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy + Alembic (planned)
- PostgreSQL 15+ (planned)
- Redis (optional, planned)

## Deployment Plan

### Phase 1 (MVP)

- Single container image.
- One service instance.
- No database dependency in current implementation.
- Optional PostgreSQL/Redis integration planned for next phases.

Gameplay mode for MVP:
- One active player per game session.
- No shared world state between players.
- Leaderboard and profiles remain persisted via HTTP + PostgreSQL.

### Phase 2 (Scale)

- Multiple service instances behind load balancer.
- Sticky routing (or allocator) by `session_id`.
- Redis for cross-instance presence and control signaling.
- Keep each game session single-writer on one instance.

## Non-Goals for MVP

- No microservice split of auth/cache/game runtime.
- No cross-region consistency.
- No UDP transport.

