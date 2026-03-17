# RiverRaid Documentation

This folder contains project documentation for **RiverRaid** (2D single-player web game with realtime authoritative backend).

## Demo

![Demo screenshot 1](./demo/Screenshot%202026-03-11%20231905.png)

![Demo screenshot 2](./demo/Screenshot%202026-03-11%20231931.png)

[Watch demo video](./demo/ApplicationFrameHost_riSHgOc3kk.mp4)

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

- Phase 0 backend is implemented: name-only login, JWT issuance/validation, WebSocket gameplay, and Docker runtime.
- Server-authoritative single-player session loop is active over WebSocket.
- Protocol and HTTP contracts are test-covered for current behavior.
- PostgreSQL persistence is implemented for completed game results and top-score leaderboard queries.

## Implemented Persistence

- Completed game sessions are stored in PostgreSQL.
- Stored fields: `pilot_name`, `score`, `level`, `started_at`, `finished_at`.
- Demo UI shows the top 10 scores before the first run and refreshes again after every game over.

## Configuration and Secrets

- Local development defaults are allowed when `APP_ENV != prod`.
- Production (`APP_ENV=prod`) requires explicit `JWT_SECRET` and `DATABASE_URL`.
- Render-style database URLs are normalized automatically:
	- `postgres://...` -> `postgresql+asyncpg://...`
	- `postgresql://...` -> `postgresql+asyncpg://...`
- Never commit secrets to the repository.

Recommended production environment variables:

- `APP_ENV=prod`
- `JWT_SECRET=<long-random-secret>`
- `DATABASE_URL=<Render internal Postgres URL>`
- `JWT_ALGORITHM=HS256`
- `ACCESS_TOKEN_TTL_SECONDS=3600`

## Render Deployment Notes

- Use a Render Web Service for the FastAPI app.
- Use a Render PostgreSQL instance for persistent storage.
- Pass the database connection string through `DATABASE_URL` as a secret environment variable.
- The app uses SQLAlchemy async mode with `asyncpg`; no `psycopg2` package is required.

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
- Demo page: `http://localhost:8000/`
- HTTP health: `http://localhost:8000/healthz`
- HTTP login: `POST http://localhost:8000/api/v1/auth/login`
- HTTP top scores: `GET http://localhost:8000/api/v1/scores`
- WebSocket: `ws://localhost:8000/ws`
