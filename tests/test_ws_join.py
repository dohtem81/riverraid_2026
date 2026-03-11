def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "pilot", "password": "pilot1234"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_ws_join_missing_token_returns_error(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {}})
        message = websocket.receive_json()
        assert message["type"] == "error"
        assert message["payload"]["code"] == "UNAUTHORIZED"


def test_ws_join_invalid_token_returns_error(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": "bad-token"}})
        message = websocket.receive_json()
        assert message["type"] == "error"
        assert message["payload"]["code"] == "UNAUTHORIZED"


def test_ws_join_valid_token_returns_join_ack(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json(
            {
                "type": "join",
                "seq": 1,
                "payload": {
                    "access_token": token,
                },
            }
        )
        message = websocket.receive_json()
        assert message["type"] == "join_ack"
        assert message["payload"]["player_id"] == "11111111-1111-1111-1111-111111111111"
        assert message["payload"]["tick_rate"] == 30
