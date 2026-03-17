# HTTP API (Current Phase 0)

## Purpose

Define non-realtime REST endpoints currently exposed by the backend.

- REST currently handles name-based auth, leaderboard retrieval, and health/demo endpoints.
- WebSocket handles realtime simulation and gameplay state.

## Base

- Base URL: `/api/v1`
- Auth: `Authorization: Bearer <token>` is required for WebSocket `join` payload
- Content type: `application/json`

## Error Format

All error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

Current HTTP status usage in this codebase:
- `200` success
- `400` invalid player name / invalid request data
- `501` not implemented (Phase 0 placeholders)

## Implemented Endpoints

### `GET /`

Returns the HTML demo page used to manually exercise auth + WebSocket gameplay.

### `GET /healthz`

Returns service health:

```json
{
  "status": "ok",
  "mode": "phase0-config-auth"
}
```

### `POST /auth/login`

Phase 0 auth is name-based and container-friendly.

- The client sends only a player name.
- The backend derives a stable `player_id` from that name.

Issue JWT/session token.

Request:
```json
{
  "username": "captain_neo"
}
```

Response `200`:
```json
{
  "access_token": "jwt_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "player_id": "11111111-1111-1111-1111-111111111111"
}
```

Validation behavior:
- Reject blank names.
- Return `400` with `INVALID_PLAYER_NAME` for empty/whitespace-only names.

### `GET /scores`

Returns the top 10 completed game results ordered by score descending.

Response `200`:
```json
[
  {
    "pilot_name": "captain_neo",
    "score": 1200,
    "level": 7,
    "finished_at": "2026-03-17T10:00:00+00:00"
  }
]
```

Notes:
- Used by the demo page leaderboard.
- Queried before the first game and after every game over.

### `POST /auth/register`

Not implemented in Phase 0.

### `POST /auth/refresh`

Not implemented in Phase 0.

### `POST /auth/logout`

Not implemented in Phase 0.

All three endpoints return `501`:

```json
{
  "error": {
    "code": "NOT_IMPLEMENTED_PHASE0",
    "message": "This endpoint is not available in Phase 0"
  }
}
```

## Security Notes

- `JWT_SECRET` and `DATABASE_URL` must be supplied explicitly in production.
- Render Postgres URLs are normalized to the async SQLAlchemy driver format used by the app.
- JWT expiry remains short-lived.

## Notes on Scope

- `GET /players/me` and persistent profile endpoints are not implemented in Phase 0.
