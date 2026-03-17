# Data Model (MVP v1)

## Current Status

- The backend now persists completed game results to PostgreSQL.
- Authentication remains name-based and does not use a `players` table yet.

## Purpose

Define persistent entities for RiverRaid score tracking and future player/account expansion.

## Database Standards

- Engine: PostgreSQL
- IDs: UUID everywhere
- Time fields: UTC `timestamptz`

## Current Implemented Table

## `game_results`

Stores one row per completed run.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Score row ID |
| pilot_name | varchar(128) not null | Player-entered display name |
| score | integer not null | Final run score |
| level | integer not null | Level reached when the game finished |
| started_at | timestamptz not null | UTC game start time |
| finished_at | timestamptz not null | UTC game finish time |

Indexes:
- index(`pilot_name`)
- index(`score` desc)

## Planned Future Tables

## `players`

Possible future account/profile table if the game evolves beyond name-only login.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Player ID |
| username | varchar(32) unique not null | Public name |
| best_score | integer not null default 0 | Cached best score |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

## `player_sessions`

Possible future refresh-token/session storage.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Session row ID |
| player_id | uuid not null | FK -> `players.id` |
| refresh_token_hash | text not null | Never store plaintext token |
| issued_at | timestamptz not null | |
| expires_at | timestamptz not null | |
| revoked_at | timestamptz null | |
| created_at | timestamptz not null | |

## Optional (Later)

## `player_checkpoints`

Persists last safe spawn bridge for reconnect/resume.

| Field | Type | Notes |
|---|---|---|
| player_id | uuid (pk) | FK -> `players.id` |
| bridge_index | integer not null | Last reached bridge |
| level_seed | text not null | Seed ID for deterministic restore |
| updated_at | timestamptz not null | |

## Migration Strategy

1. Current schema: `game_results`.
2. Add `players` and `player_sessions` if account-based auth is introduced.
3. Add `player_checkpoints` when reconnect/resume persistence is enabled.

