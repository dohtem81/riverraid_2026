# RiverRaid Documentation

This folder contains project documentation for **RiverRaid** (2D single-player web game with realtime authoritative backend).

## Docs Index

- [Game Vision](./game-vision.md)
- [System Design](./system_design.md)
- [MVP Scope](./mvp-scope.md)
- [Technical Architecture](./technical-architecture.md)
- [Realtime Protocol](./realtime-protocol.md)
- [Data Model](./data-model.md)
- [HTTP API](./api-http.md)
- [Login Cache Service](./login-cache-service.md)
- [Roadmap](./roadmap.md)

## Current Focus

- Define MVP gameplay loop and constraints.
- Confirm server-authoritative realtime architecture.
- Lock protocol + schema contracts for first playable version.
- Implement Phase 0 backend (config-auth, Docker runtime, unit test gate).

## Docker Quick Start (Phase 0)

Run backend:

```bash
docker compose up --build backend
```

Run unit tests in container:

```bash
docker compose run --rm tests
```

Runtime endpoints:
- HTTP health: `http://localhost:8000/healthz`
- HTTP login: `POST http://localhost:8000/api/v1/auth/login`
- WebSocket: `ws://localhost:8000/ws`
