# HTTP API (Current Phase 0)

## Purpose

Define non-realtime REST endpoints currently exposed by the backend.

- REST currently handles config-backed auth and health/demo endpoints.
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
- `401` invalid credentials
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

Phase 0 auth is config-backed (development mode) and container-friendly.

- One configured user is loaded from environment/config.
- JWT subject (`sub`) maps to configured `AUTH_PLAYER_ID`.

Issue JWT/session token.

Request:
```json
{
  "username": "captain_neo",
  "password": "strong_password"
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
- Verify `username` + `password` against configured values.
- Return `401` for invalid username/password.

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

- Config auth is for development only.
- JWT expiry remains short-lived.

## Notes on Scope

- `GET /players/me`, leaderboard, and persistent profile endpoints are planned but not implemented in Phase 0.
