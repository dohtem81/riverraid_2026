# RiverRaid 2026

![RiverRaid 2026 demo](docs/demo/demoplay.gif)

Server-authoritative River Raid prototype built with FastAPI, WebSocket gameplay, JWT-based session join, and PostgreSQL-backed finished-game persistence.

Try it online: https://riverraid-2026.onrender.com/

## Architecture (Key Idea)

- Server runs the entire game simulation (authoritative state)
- Client is a thin WebSocket renderer (no game logic)
- State is streamed in real-time to the browser

This design enables deterministic gameplay, persistence, and future multiplayer support.

## Features

- Name-only login flow
- Server-authoritative realtime gameplay over WebSocket
- **River**: Procedurally generated, continuously scrolling. River narrows and curves at bridges.
- **Fuel system**: Fuel burns continuously; fly over a fuel station to refill. Crashing ends a life.
- **Missiles**: Player fires upward (Space key). 0.5 s cooldown, 2 s lifetime.
- **Helicopters**: Patrol laterally within the river. Spawn in level-sized groups (1 per group at level 1, 2 at level 2, etc.), stacked vertically with random X positions. Mirror their sprite to always face direction of travel.
- **Tanks**: Appear on both river banks at level 2+. Fire horizontal missiles across the river every 2 s.
- **Jets**: Fast horizontally crossing enemies unlocked at level 3.
- **Bridges**: Mark level transitions. Shooting a bridge awards +20 pts; colliding damages the plane.
- **Enemy scaling**: Spawn frequency increases +10% per level for all enemy types.
- **Scoring**: fuel station +10 · bridge +20 · helicopter +10 · tank +30
- Persistent finished-game results stored in PostgreSQL; top-10 leaderboard before first run and after each game over
- Docker-based local development and test workflow

## Local Development

### Start the backend

```bash
docker compose up --build backend
```

### Run tests

```bash
docker compose build tests
docker compose run --rm tests pytest -q
```

## Local Endpoints

- Demo page: `http://localhost:8000/`
- Health check: `http://localhost:8000/healthz`
- Login: `POST http://localhost:8000/api/v1/auth/login`
- Top scores: `GET http://localhost:8000/api/v1/scores`
- WebSocket: `ws://localhost:8000/ws`

## Configuration

- Local development defaults are used when `APP_ENV != prod`.
- Production (`APP_ENV=prod`) requires explicit `JWT_SECRET` and `DATABASE_URL`.
- Render-style database URLs are normalized automatically (`postgres://...` → `postgresql+asyncpg://...`).
- Never commit secrets to the repository.

## Render Deployment

### Services

Create:
- 1 Render Web Service for the app
- 1 Render PostgreSQL instance

### Environment Variables

Set these on the Web Service:

- `APP_ENV=prod`
- `JWT_SECRET=<long-random-secret>`
- `DATABASE_URL=<Render internal Postgres URL>`
- `JWT_ALGORITHM=HS256`
- `ACCESS_TOKEN_TTL_SECONDS=3600`

### Build / Start

- Build command:

```bash
pip install --upgrade pip && pip install .
```

- Start command:

```bash
uvicorn riverraid.main:app --host 0.0.0.0 --port $PORT
```

## Documentation

- [Game Vision](docs/game-vision.md)
- [System Design](docs/system_design.md)
- [MVP Scope](docs/mvp-scope.md)
- [Technical Architecture](docs/technical-architecture.md)
- [Realtime Protocol](docs/realtime-protocol.md)
- [Data Model](docs/data-model.md)
- [HTTP API](docs/api-http.md)
- [Login Cache Service](docs/login-cache-service.md)
- [Roadmap](docs/roadmap.md)
