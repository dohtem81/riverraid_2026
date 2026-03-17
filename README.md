# RiverRaid 2026

Server-authoritative River Raid prototype built with FastAPI, WebSocket gameplay, JWT-based session join, and PostgreSQL-backed finished-game persistence.

## Features

- Name-only login flow
- Server-authoritative realtime gameplay over WebSocket
- Persistent finished-game results stored in PostgreSQL
- Top 10 leaderboard shown before first game and after each game over
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

### Important Notes

- Do not commit secrets to git.
- Store `JWT_SECRET` and `DATABASE_URL` as Render secret environment variables.
- Render may provide `DATABASE_URL` as `postgres://...` or `postgresql://...`; the app normalizes that automatically to the async SQLAlchemy format required by `asyncpg`.
- `JWT_SECRET` is the private signing key used to issue and validate access tokens.

### Build / Start

Suggested Render settings:

- Build command:

```bash
pip install --upgrade pip && pip install .
```

- Start command:

```bash
uvicorn riverraid.main:app --host 0.0.0.0 --port $PORT
```

## Documentation

See the detailed project docs in [docs/README.md](docs/README.md).
