# Data Model (MVP v1)

## Current Status

- The backend persists game sessions to PostgreSQL in two steps: a row is **inserted at game start** and **updated at game finish**.
- Rows with `finished_at = NULL` represent games that were started but not yet finished, enabling analysis of abandonment rate.
- Authentication remains name-based and does not use a `players` table yet.

## Purpose

Define persistent entities for RiverRaid score tracking and future player/account expansion.

## Database Standards

- Engine: PostgreSQL
- IDs: UUID everywhere
- Time fields: UTC `timestamptz`

## Current Implemented Table

## `game_results`

Stores one row per game session. The row is **inserted when the game starts** (with `score=0`, `level=1`, `finished_at=NULL`) and **updated when the game ends** (with the final score, level, and finish timestamp).

Rows where `finished_at IS NULL` represent games that were started but abandoned before finishing.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Row ID |
| session_id | varchar(36) unique not null | Per-game UUID generated at join/restart |
| pilot_name | varchar(128) not null | Player-entered display name |
| score | integer not null default 0 | Final run score (0 until game finishes) |
| level | integer not null default 1 | Level reached (1 until game finishes) |
| started_at | timestamptz not null | UTC game start time |
| finished_at | timestamptz null | UTC game finish time; NULL means in-progress or abandoned |

Indexes:
- unique index(`session_id`)
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

1. Current schema: `game_results` (two-step insert/update lifecycle).
2. Schema migrations are applied automatically at startup via `migrate_db()` in `infrastructure/database.py`. It inspects live table columns and issues `ALTER TABLE` statements for any missing or incorrectly constrained columns — safe to run on every startup against both fresh and existing databases.
3. Add `players` and `player_sessions` if account-based auth is introduced.
4. Add `player_checkpoints` when reconnect/resume persistence is enabled.

