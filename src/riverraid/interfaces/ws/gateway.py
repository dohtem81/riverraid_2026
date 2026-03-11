from datetime import UTC, datetime
from uuid import uuid4

from fastapi import WebSocket

from riverraid.application.use_cases import ValidateJoinToken
from riverraid.infrastructure.jwt_token_service import TokenValidationError


class WebSocketGateway:
    def __init__(self, validate_join_token: ValidateJoinToken) -> None:
        self._validate_join_token = validate_join_token

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        session_id = f"sess_{uuid4().hex[:10]}"
        joined = False

        try:
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")
                seq = message.get("seq", 0)

                if msg_type == "join":
                    token = (message.get("payload") or {}).get("access_token")
                    if not token:
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Missing access token"))
                        continue

                    try:
                        player = self._validate_join_token.execute(token)
                    except TokenValidationError:
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Invalid access token"))
                        continue

                    joined = True
                    await websocket.send_json(
                        {
                            "type": "join_ack",
                            "ts": self._now_ms(),
                            "session_id": session_id,
                            "seq": 1,
                            "payload": {
                                "player_id": player.player_id,
                                "tick_rate": 30,
                                "snapshot_rate": 12,
                            },
                        }
                    )
                    continue

                if msg_type == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "ts": self._now_ms(),
                            "session_id": session_id,
                            "seq": seq,
                            "payload": {
                                "nonce": (message.get("payload") or {}).get("nonce"),
                            },
                        }
                    )
                    continue

                if msg_type == "input":
                    if not joined:
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Join required before input"))
                        continue

                    await websocket.send_json(
                        {
                            "type": "event",
                            "ts": self._now_ms(),
                            "session_id": session_id,
                            "seq": seq,
                            "payload": {
                                "event_type": "input_accepted",
                                "data": {
                                    "input_seq": (message.get("payload") or {}).get("input_seq", 0),
                                },
                            },
                        }
                    )
                    continue

                await websocket.send_json(self._error_payload(seq=seq, code="INVALID_TYPE", message="Unknown message type"))
        except Exception:
            await websocket.close()

    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(UTC).timestamp() * 1000)

    def _error_payload(self, seq: int, code: str, message: str) -> dict:
        return {
            "type": "error",
            "ts": self._now_ms(),
            "seq": seq,
            "payload": {
                "code": code,
                "message": message,
            },
        }
