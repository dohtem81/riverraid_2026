# HTTP API (MVP)

## Purpose

Define non-realtime REST endpoints that complement the WebSocket protocol.

- REST handles auth, bootstrap data, and read-heavy UI calls.
- WebSocket handles realtime simulation and gameplay state.

## Base

- Base URL: `/api/v1`
- Auth: `Authorization: Bearer <token>` for protected endpoints
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

Common HTTP status usage:
- `200` success read
- `201` created
- `400` validation error
- `401` unauthorized
- `403` forbidden
- `404` not found
- `409` conflict
- `429` rate limit

## Auth

Phase 0 auth is config-backed (development mode) and container-friendly.

- One configured user is loaded from environment/config.
- `POST /auth/login` validates against configured credentials.
- JWT subject (`sub`) maps to configured `AUTH_PLAYER_ID`.
- `POST /auth/register`, `POST /auth/refresh`, and `POST /auth/logout` return `501` in Phase 0.

### `POST /auth/register`

Create account (not implemented in Phase 0).

Response `501`:
```json
{
  "error": {
    "code": "NOT_IMPLEMENTED_PHASE0",
    "message": "This endpoint is not available in Phase 0"
  }
}
```

### `POST /auth/login`

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

### `POST /auth/refresh`

Refresh token flow is not implemented in Phase 0.

Response `501`:
```json
{
  "error": {
    "code": "NOT_IMPLEMENTED_PHASE0",
    "message": "This endpoint is not available in Phase 0"
  }
}
```

### `POST /auth/logout`

Logout/revoke flow is not implemented in Phase 0.

Response `501`:
```json
{
  "error": {
    "code": "NOT_IMPLEMENTED_PHASE0",
    "message": "This endpoint is not available in Phase 0"
  }
}
```

## Player

### `GET /players/me`

Returns authenticated player profile.

Status:
- Not implemented in Phase 0 (`501` if exposed).

Response `200`:
```json
{
  "id": "2a3d8d0e-3f09-4d43-8e22-2ce3551a22ca",
  "username": "captain_neo",
  "best_score": 4200,
  "total_kills": 73
}
```

## Leaderboard

### `GET /leaderboard?limit=20`

Returns top scores.

Status:
- Not implemented in Phase 0 (`501` if exposed).

Response `200`:
```json
{
  "items": [
    {
      "rank": 1,
      "player_id": "2a3d8d0e-3f09-4d43-8e22-2ce3551a22ca",
      "username": "captain_neo",
      "score": 4200,
      "created_at": "2026-03-10T16:23:45Z"
    }
  ]
}
```

## Security + Limits

- Config auth is for development only.
- Rate limit should be enabled on `/auth/login`.
- JWT expiry remains short-lived.
- Input validation on all query/body params.

## Notes on Scope

- Optional future HTTP admin endpoints are out of MVP scope.
