# Realtime Protocol (MVP v1)

## Scope

Defines client↔server WebSocket message contracts for authoritative River Raid gameplay.

## Transport

- Protocol: WebSocket over TLS (`wss`).
- Serialization: JSON for MVP.
- Compression: optional permessage-deflate.

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

Sent once after socket open.

```json
{
	"type": "join",
	"ts": 1741600000000,
	"seq": 1,
	"payload": {
		"access_token": "<jwt>",
		"client_version": "0.1.0"
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
		"thrust": "fast",
		"turn": "left",
		"fire": true,
		"dock_request": false
	}
}
```

Rules:
- `input_seq` must be strictly increasing per client.
- Server may drop stale/duplicate inputs.

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
		"snapshot_rate": 12
	}
}
```

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
		"player": {
			"x": 103.2,
			"y": 455.0,
			"vx": 0.0,
			"vy": 5.2,
			"fuel": 72,
			"hp": 3,
			"score": 180
		},
		"entities": [
			{
				"id": "enemy_1",
				"kind": "helicopter",
				"x": 120.0,
				"y": 420.0,
				"hp": 1
			}
		]
	}
}
```

### `event`

Discrete game event (bridge destroyed, refuel, death, respawn).

```json
{
	"type": "event",
	"ts": 1741600000090,
	"session_id": "sess_abc123",
	"seq": 145,
	"payload": {
		"event_type": "bridge_destroyed",
		"data": {
			"bridge_id": "b12",
			"score_delta": 50
		}
	}
}
```

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
- Server applies `input` by `input_seq`; duplicates are ignored.
- Client uses `last_processed_input_seq` for reconciliation.
- No retransmit at protocol layer in MVP.

## Tick and Broadcast Policy

- Simulation tick rate: 30 TPS.
- Snapshot broadcast: 10–15 Hz.
- Event messages are sent immediately after tick resolution.

## Reconnect Policy

- On disconnect, server keeps player slot for 15 seconds.
- Rejoin with valid token restores binding if session is active.
- On successful rejoin, server sends immediate `snapshot` and pending critical events.

## Validation + Limits

- Max input payload size (e.g., 1 KB).
- Max input message rate per client (e.g., 60/s).
- Reject unknown message types.
- Server clamps impossible control values.

