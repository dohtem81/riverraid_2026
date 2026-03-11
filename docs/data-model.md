# Data Model (MVP v1)

## Purpose

Define persistent entities for RiverRaid authentication, player progression, and score tracking.

## Database Standards

- Engine: PostgreSQL
- IDs: UUID everywhere
- Time fields: UTC `timestamptz`

## Core Tables

## `players`

Stores player identity and account-level progression.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Player ID |
| username | varchar(32) unique not null | Public name |
| password_hash | text not null | Argon2/Bcrypt hash |
| best_score | integer not null default 0 | Cached best score |
| total_kills | integer not null default 0 | Lifetime kills |
| created_at | timestamptz not null | |
| updated_at | timestamptz not null | |

Indexes:
- unique(`username`)

## `player_sessions`

Tracks active/refresh token metadata for session management.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Session row ID |
| player_id | uuid not null | FK -> `players.id` |
| refresh_token_hash | text not null | Never store plaintext token |
| issued_at | timestamptz not null | |
| expires_at | timestamptz not null | |
| revoked_at | timestamptz null | |
| created_at | timestamptz not null | |

Indexes:
- index(`player_id`)
- index(`expires_at`)

## `highscores`

Stores score outcomes per completed run.

| Field | Type | Notes |
|---|---|---|
| id | uuid (pk) | Score row ID |
| player_id | uuid not null | FK -> `players.id` |
| score | integer not null | Final run score |
| bridge_reached | integer not null default 0 | Progress marker |
| duration_seconds | integer not null default 0 | Run duration |
| created_at | timestamptz not null | |

Indexes:
- index(`player_id`, `score` desc)
- index(`score` desc)

## Optional (Phase 2)

## `player_checkpoints`

Persists last safe spawn bridge for reconnect/resume.

| Field | Type | Notes |
|---|---|---|
| player_id | uuid (pk) | FK -> `players.id` |
| bridge_index | integer not null | Last reached bridge |
| level_seed | text not null | Seed ID for deterministic restore |
| updated_at | timestamptz not null | |

## Migration Strategy

1. Baseline migration: `players`, `player_sessions`, `highscores`.
2. Add `player_checkpoints` when reconnect/resume persistence is enabled.

