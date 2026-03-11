# System Design (MVP v1)

## Purpose

Define the runtime architecture for a web-based River Raid single-player prototype with a server-authoritative realtime backend.

## Design Goals

- Low-latency realtime control and combat.
- Authoritative simulation to prevent cheating.
- Simple deployment for MVP, with a clear scale path.
- Explicit boundaries between HTTP auth/bootstrap and WebSocket gameplay.
- Single-player session runtime with persistent profile/highscore backend.

## Topology

Single deployable service (modular monolith):

1. HTTP API module (auth, profile, bootstrap)
2. Realtime gateway (WebSocket session management)
3. Game session runtime (authoritative tick loop)
4. Persistence adapter (PostgreSQL read/write)
5. Optional cache adapter (Redis for session/presence/rate limiting)

For MVP, all modules run in one process image and one database.

## Clean Architecture Mapping

### Domain Layer

- Owns game simulation rules, anti-cheat constraints, and invariant checks.
- Contains no transport/persistence/framework code.

### Application Layer

- Exposes use cases:
	- `LoginWithConfiguredCredentials`
	- `IssueAccessToken`
	- `ValidateWebSocketJoin`
	- `ApplyPlayerInput`
	- `BuildAuthoritativeSnapshot`
- Defines required ports:
	- `CredentialProviderPort`
	- `TokenServicePort`
	- `SessionStatePort`
	- `ClockPort`

### Interface Adapters Layer

- HTTP controllers call Application use cases and return API error envelope.
- WebSocket gateway maps protocol messages (`join`, `input`, `ping`) to use-case requests.
- Config adapter resolves Phase 0 user credentials and `player_id`.
- Presenter maps use-case responses to HTTP JSON and WS payload shapes.

### Infrastructure Layer

- FastAPI/Uvicorn runtime.
- JWT signer/verifier implementation.
- Config loader from mounted file/env.
- Container boot entrypoint and health checks.
- Optional Phase 1 adapters for PostgreSQL/Redis.

## Phase 0 Runtime Policy

- Single-player only: one active player per `session_id`.
- No persistence dependency at startup.
- Containerized runtime is required.
- Non-login auth endpoints are present but return `501`.

## Unit Test Policy by Layer

- Domain tests: pure rule validation (no mocks for frameworks).
- Application tests: use-case behavior with fake/mock ports.
- Adapter tests: HTTP login contract, HTTP `501` contracts, WS join token validation.
- CI gate: test suite must pass before image build/publish.

## Runtime Components

### 1) HTTP API

Responsibilities:
- Registration and login.
- Token refresh/revoke.
- Fetch player profile and lightweight bootstrap payload.

Does not run simulation logic.

### 2) Realtime Gateway

Responsibilities:
- Upgrade authenticated clients to WebSocket.
- Validate token and bind `player_id` to a game session.
- Enforce per-connection rate limits and payload validation.
- Route validated `input` messages to the session runtime.

### 3) Game Session Runtime (Authoritative)

Responsibilities:
- Own a single match/level simulation state.
- Run one active player per session in MVP.
- Run fixed tick loop (target: 30 TPS).
- Apply validated player inputs in tick order.
- Resolve collisions/combat/scoring/fuel.
- Emit snapshots (10–15 Hz) and gameplay events.

This is the only writer for in-memory match state.

### 4) Persistence Adapter

Responsibilities:
- Load durable player state at join/spawn.
- Persist checkpoints and session-end outcomes.
- Write highscores and progression.

Avoid per-tick DB writes. Use checkpointed or event-triggered persistence.

### 5) Redis (Optional in MVP)

Use only for:
- Sliding login/profile cache.
- Token denylist / refresh token metadata.
- Cross-instance presence when scaling.

Do not use Redis as authoritative simulation state.

## Data Flow

### Login + Join

1. Client calls HTTP login and receives JWT access token.
2. Client opens WebSocket with token.
3. Gateway authenticates and attaches player to a dedicated single-player game session.
4. Runtime loads spawn/checkpoint state and emits `join_ack` + initial snapshot.

### Realtime Loop

1. Client sends compact input commands with monotonically increasing `input_seq`.
2. Runtime applies inputs at next tick after validation.
3. Runtime emits snapshots/events including `last_processed_input_seq`.
4. Client reconciles predicted state with authoritative snapshot.

### Persist

- On bridge reached, death, refuel milestone, or match end: write durable updates.

## Scaling Plan

### Phase 1 (MVP)

- 1 service instance.
- 1 PostgreSQL instance.
- Optional Redis.
- Single-player sessions only (one player per session).

### Phase 2

- Horizontal scale service instances.
- Sticky routing by `session_id` (or dedicated session allocator).
- Redis pub/sub for cross-instance presence and control signals.
- Keep each game session single-writer on exactly one instance.

## Failure Handling

- If DB unavailable: reject new joins requiring persistence; keep existing sessions alive where possible.
- If Redis unavailable: continue operation using DB fallback.
- On WebSocket disconnect: retain player slot briefly (reconnect grace window, e.g., 15s).
- On reconnect: restore session binding and send fresh snapshot.

## Security and Anti-Cheat

- Server authoritative movement/combat/fuel.
- Input rate limits and schema validation.
- Clamp impossible deltas (turn rate, fire rate, speed).
- JWT short-lived access tokens; refresh token rotation/revocation for HTTP auth.

## Observability (Minimum)

- Structured logs with `player_id`, `session_id`, message type, and latency.
- Metrics:
	- tick duration p50/p95
	- WS connected clients
	- dropped/invalid inputs
	- snapshot fanout time
	- auth failures/rate limit hits

