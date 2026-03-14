# Realtime Protocol (Current Phase 0)

## Scope

Defines currently implemented client↔server WebSocket message contracts.

## Transport

- Protocol: WebSocket (`ws://localhost:8000/ws` in local/docker dev)
- Serialization: JSON

## Envelope

All messages use this top-level shape:

```json
{
	"type": "input",
	"ts": 1741600000123,
	"session_id": "sess_abc123",
	"seq": 42,
	"payload": {}
}
```

Fields:
- `type` (string): message kind.
- `ts` (number): sender unix epoch ms.
- `session_id` (string): assigned by server after join.
- `seq` (number): sender-local sequence for this stream.
- `payload` (object): typed body.

## Client → Server Messages

### `join`

Sent after socket open.

```json
{
	"type": "join",
	"ts": 1741600000000,
	"seq": 1,
	"payload": {
		"access_token": "<jwt>"
	}
}
```

### `input`

Legacy typed-input command (still accepted). Prefer `keydown`/`keyup` for smooth movement.

```json
{
	"type": "input",
	"ts": 1741600000050,
	"session_id": "sess_abc123",
	"seq": 2,
	"payload": {
		"input_seq": 106,
		"turn": "left",
		"fast": true,
		"fire": true
	}
}
```

Input rules:
- `input_seq` is optional for thin clients; if omitted, server derives it from message `seq`.
- `turn` accepts only `left`, `right`, or omitted.
- `fast` is optional boolean (`false` when omitted).
- `fire` is optional boolean (`false` when omitted).
- Server rejects invalid input payloads with `error.code=INVALID_INPUT`.
- On accepted input, server emits `event:event_type=input_accepted` and then a `snapshot`.

### `keydown`

Key-press event. Server records the key in an active set and applies continuous movement each tick while the key is held. Preferred over `input` for smooth movement (avoids OS key-repeat pause).

```json
{
	"type": "keydown",
	"seq": 3,
	"payload": {
		"key": "ArrowLeft"
	}
}
```

Accepted key values: `ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`, `Space` (also `Spacebar`, `" "`). Server normalises to `left`, `right`, `up`, `down`, `space`.

- `Space`/`Spacebar` fires a missile (subject to `missile_cooldown_seconds`).
- Unknown keys are rejected with `error.code=INVALID_INPUT`.
- Server emits `event:event_type=input_accepted` with `key_event=keydown` and `key=<normalised>`.

### `keyup`

Key-release event. Server removes the key from the active set so movement stops.

```json
{
	"type": "keyup",
	"seq": 4,
	"payload": {
		"key": "ArrowLeft"
	}
}
```

Same key validation as `keydown`. Emits `event:event_type=input_accepted` with `key_event=keyup`.

### `ping`

Keepalive and RTT measurement.

```json
{
	"type": "ping",
	"ts": 1741600000100,
	"seq": 9,
	"payload": {
		"nonce": "n123"
	}
}
```

### `restart`

Sent by client after game over to start again.

```json
{
	"type": "restart",
	"ts": 1741600000200,
	"seq": 10,
	"payload": {}
}
```

## Server → Client Messages

### `join_ack`

```json
{
	"type": "join_ack",
	"ts": 1741600000010,
	"session_id": "sess_abc123",
	"seq": 1,
	"payload": {
		"player_id": "2a3d...",
		"tick_rate": 30,
		"snapshot_rate": 12,
		"render_config": {
			"world_width": 1000,
			"viewport_height": 600
		}
	}
}
```

After `join_ack`, server immediately sends an initial `snapshot` with the plane actor spawn.
- Spawn position for Phase 0: near bottom of visible viewport.
- Initial plane coordinates: `x=500`, `y=60` (world-space relative to `camera_y=0`).

### `snapshot`

Authoritative state snapshot.

```json
{
	"type": "snapshot",
	"ts": 1741600000083,
	"session_id": "sess_abc123",
	"seq": 144,
	"payload": {
		"tick": 2190,
		"last_processed_input_seq": 106,
		"camera_y": 320.0,
		"hud": {
			"lives": 3,
			"score": 180,
			"level": 1,
			"fuel": 72
		},
		"player": {
			"x": 103.2,
			"y": 455.0,
			"vx": 0.0,
			"vy": 5.2,
			"fuel": 72,
			"hp": 3,
			"score": 180,
			"actor": "plane"
		},
		"river_banks": [
			{
				"y": 0,
				"left_x": 280,
				"right_x": 700
			}
		],
		"entities": [
			{
				"id": "fuel_1",
				"kind": "fuel_station",
				"x": 520.0,
				"y": 360.0,
				"width": 16.0,
				"height": 240.0,
				"label": "FUEL"
			},
			{
				"id": "missile_3",
				"kind": "missile",
				"x": 500.0,
				"y": 520.0,
				"width": 4.0,
				"height": 12.0
			},
			{
				"id": "bridge_2",
				"kind": "bridge",
				"x": 500.0,
				"y": 800.0,
				"left_x": 300.0,
				"right_x": 700.0,
				"width": 400.0,
				"height": 20.0
			},
			{
				"id": "heli_1",
				"kind": "helicopter",
				"x": 450.0,
				"y": 680.0,
				"width": 40.0,
				"height": 20.0
			},
			{
				"id": "tank_1",
				"kind": "tank",
				"x": 240.0,
				"y": 750.0,
				"width": 20.0,
				"height": 14.0,
				"side": "left"
			},
			{
				"id": "tank_missile_2",
				"kind": "tank_missile",
				"x": 265.0,
				"y": 757.0,
				"width": 10.0,
				"height": 4.0
			}
		]
	}
}
```

### `event`

Discrete game event.

```json
{
	"type": "event",
	"ts": 1741600000090,
	"session_id": "sess_abc123",
	"seq": 145,
	"payload": {
		"event_type": "input_accepted",
		"data": {
			"input_seq": 106,
			"turn": "left",
			"fast": true,
			"fire": true
		}
	}
}
```

Additional events used in current Phase 0:
- `input_accepted` — input or key event was processed; `data` contains echo of the command.
- `collision_bank` — plane touched a river bank; lives reduced.
- `collision_bridge` — plane touched a bridge; lives reduced.
- `collision_helicopter` — plane collided with a helicopter; lives reduced.
- `collision_tank_missile` — a tank missile hit the plane; lives reduced.
- `crash_fuel` — fuel reached 0; life reduced and crash applied.
- `game_over` — lives reached 0; gameplay simulation paused.
- `game_restarted` — restart accepted; state reset.

### `pong`

```json
{
	"type": "pong",
	"ts": 1741600000101,
	"session_id": "sess_abc123",
	"seq": 146,
	"payload": {
		"nonce": "n123"
	}
}
```

### `error`

```json
{
	"type": "error",
	"ts": 1741600000102,
	"seq": 147,
	"payload": {
		"code": "INVALID_INPUT",
		"message": "turn value is invalid"
	}
}
```

## Ordering + Reliability

- WebSocket provides ordered delivery per connection.
- Server returns `last_processed_input_seq` in snapshots.
- Client uses `last_processed_input_seq` for reconciliation.
- No retransmit at protocol layer in MVP.

## Tick and Broadcast Policy

- Simulation tick rate: 30 TPS.
- Snapshot broadcast: ~10 Hz (0.1s timeout loop) plus snapshots sent immediately after accepted input/restart/join.
- Event messages are sent immediately after tick resolution.
- River banks are generated on join and included in every snapshot for rendering.
- Camera advances forward at constant speed; map scrolls downward on screen as `camera_y` increases.
- New river bank segments are generated as `camera_y` approaches unseen ranges.
- River width is variable per segment: max width `420`, min width `144` (`9 x plane width`).

## Collision Event

When plane intersects river bank bounds, server emits:

```json
{
	"type": "event",
	"payload": {
		"event_type": "collision_bank",
		"data": {
			"hp": 2
		}
	}
}
```

Same structure for `collision_bridge`, `collision_helicopter`, and `collision_tank_missile`.
All collision events include `data.hp` (remaining lives) and, on fatal hits, `data.respawn_camera_y`.

## Missile Rules

- **Player missiles** travel upward at `missile_speed` game-units/second (config default: `300`).
- **Lifetime:** missiles are removed after `missile_lifetime_seconds` (default: `2.0 s`).
- **Cooldown:** minimum `missile_cooldown_seconds` between shots (default: `0.5 s`).
- Fire is triggered by a `keydown` with `key=Space`.
- Player missiles destroy fuel stations (+10 score), bridges (+20 score), helicopters (+10 score), and tanks (+30 score).

## Tank Behaviour

- Tanks spawn on the river bank edge (left or right side) at random intervals.
- Every `tank_shoot_interval_seconds` (default: `2.0 s`) a tank fires a horizontal missile across the river.
- Left-bank tanks fire right; right-bank tanks fire left.
- Tank missiles travel at `tank_missile_speed_x` (default: `200` game-units/s) and are pruned when they exit world bounds.
- A player missile that overlaps a tank destroys it and awards `tank_score` (default: +30) points.

## Game Over Behavior

- Start lives: `3`.
- Fuel burns at `1` unit per second while simulation runs.
- Refueling occurs at `20` fuel units per second while plane overlaps a fuel station.
- Fuel stations spawn randomly within river bounds with minimum spacing of 8 seconds of flight.
- Fuel station dimensions: width equals plane width, height only tall enough to cover the vertical `FUEL` letters.
- At fuel `0`, server triggers a crash (`crash_fuel`) and subtracts one life.
- Each bank, bridge, helicopter collision, or tank missile hit subtracts `1` life.
- At `0` lives, server emits `game_over` and ignores movement input (`error.code=GAME_OVER`).
- Client can send `restart` command; server resets state and emits `game_restarted` plus fresh snapshot.

## Validation + Limits

- Unknown message types are rejected with `error.code=INVALID_TYPE`.
- Input payload shape is validated (`input_seq`, `turn`, `fast`, `fire`).
- Dedicated rate limiting and payload byte limits are not implemented yet.

