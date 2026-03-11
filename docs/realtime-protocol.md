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

Primary gameplay input command.

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
- `collision_bank` - plane touched bank, lives reduced.
- `collision_bridge` - plane touched bridge, lives reduced.
- `crash_fuel` - fuel reached 0, life reduced and crash applied.
- `game_over` - lives reached 0, gameplay simulation paused.
- `game_restarted` - restart accepted, state reset.

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

## Game Over Behavior

- Start lives: `3`.
- Fuel burns at `1` unit per second while simulation runs.
- Refueling occurs at `20` fuel units per second while plane overlaps a fuel station.
- Fuel stations spawn randomly within river bounds with minimum spacing of 8 seconds of flight.
- Fuel station dimensions: width equals plane width, height only tall enough to cover the vertical `FUEL` letters.
- At fuel `0`, server triggers a crash (`crash_fuel`) and subtracts one life.
- Each bank or bridge collision subtracts `1` life.
- At `0` lives, server emits `game_over` and ignores movement input (`error.code=GAME_OVER`).
- Client can send `restart` command; server resets state and emits `game_restarted` plus fresh snapshot.

## Validation + Limits

- Unknown message types are rejected with `error.code=INVALID_TYPE`.
- Input payload shape is validated (`input_seq`, `turn`, `fast`, `fire`).
- Dedicated rate limiting and payload byte limits are not implemented yet.

