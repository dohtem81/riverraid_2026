# Login Cache Service

## Goal

On login, load player profile from Redis if recently active (last 24h). If missing, read from Postgres, then cache in Redis with 24h TTL.

## Ownership

This is a separate internal service boundary used by login/auth flow.

- Input: `player_id`
- Output: hydrated player profile + source (`redis` or `postgres`)

## Implemented Contract

Endpoint:

- `POST /internal/auth/on-login`

Request:

```json
{
  "player_id": "<uuid-or-text-id>"
}
```

Response:

```json
{
  "source": "redis",
  "ttl_seconds": 86400,
  "player": {
    "id": "...",
    "username": "...",
    "credits": 5000,
    "reputation": 0,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

## Cache-Aside Flow

1. Build cache key: `player:profile:{player_id}`.
2. Try Redis `GET`.
3. If hit: refresh TTL to 24h (`EXPIRE`) and return payload with `source=redis`.
4. If miss: query Postgres `players` table.
5. If found: Redis `SET EX 86400` and return `source=postgres`.
6. If not found: return `404`.

This is sliding expiration: active users keep their cache entry alive.

## Resilience Behavior

- Redis read/write errors are non-fatal (service falls back to Postgres read path).
- If Postgres has no matching player, request fails with `404`.

## Configuration

- `REDIS_URL`
- `DATABASE_URL`
- `LOGIN_PROFILE_CACHE_TTL_SECONDS` (default `86400`)

## Next Step (Optional)

For stronger isolation, move this logic into its own process and call it via internal HTTP/RPC from auth service.
