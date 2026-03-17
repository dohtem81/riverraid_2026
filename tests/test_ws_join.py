import random

from riverraid.interfaces.ws.gateway import WebSocketGateway


def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "pilot", "password": "pilot1234"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _receive_until_type(websocket, expected_type, max_messages=10):
    for _ in range(max_messages):
        message = websocket.receive_json()
        if message.get("type") == expected_type:
            return message
    raise AssertionError(f"Did not receive message type: {expected_type}")


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
        message = _receive_until_type(websocket, "join_ack")
        assert message["type"] == "join_ack"
        assert message["payload"]["player_id"] == "11111111-1111-1111-1111-111111111111"
        assert message["payload"]["tick_rate"] == 30
        assert message["payload"]["render_config"]["world_width"] == 1000.0
        assert message["payload"]["render_config"]["viewport_height"] == 600.0

        snapshot = _receive_until_type(websocket, "snapshot")
        assert snapshot["type"] == "snapshot"
        assert snapshot["payload"]["tick"] == 0
        assert snapshot["payload"]["player"]["actor"] == "plane"
        assert snapshot["payload"]["player"]["x"] == 500.0
        assert snapshot["payload"]["player"]["y"] == 60.0
        assert snapshot["payload"]["camera_y"] == 0.0
        assert snapshot["payload"]["hud"] == {
            "lives": 3,
            "score": 0,
            "level": 1,
            "fuel": 100,
        }
        river_banks = snapshot["payload"]["river_banks"]
        assert isinstance(river_banks, list)
        assert len(river_banks) > 10
        first_segment = river_banks[0]
        assert "y" in first_segment
        assert "left_x" in first_segment
        assert "right_x" in first_segment
        assert first_segment["left_x"] < first_segment["right_x"]

        widths = [segment["right_x"] - segment["left_x"] for segment in river_banks]
        assert min(widths) >= 48.0
        assert max(widths) <= 420.0
        assert max(widths) - min(widths) > 0.0


def test_ws_input_accepts_left_right_fast_fire(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        join_ack = _receive_until_type(websocket, "join_ack")
        assert join_ack["type"] == "join_ack"
        snapshot = _receive_until_type(websocket, "snapshot")
        assert snapshot["type"] == "snapshot"

        websocket.send_json(
            {
                "type": "input",
                "seq": 2,
                "payload": {
                    "input_seq": 10,
                    "turn": "left",
                    "fast": True,
                    "fire": True,
                },
            }
        )
        event = _receive_until_type(websocket, "event")
        assert event["type"] == "event"
        assert event["payload"]["event_type"] == "input_accepted"
        assert event["payload"]["data"] == {
            "input_seq": 10,
            "turn": "left",
            "fast": True,
            "fire": True,
        }
        snapshot_after_left = _receive_until_type(websocket, "snapshot")
        assert snapshot_after_left["type"] == "snapshot"
        assert snapshot_after_left["payload"]["player"]["x"] == 495.0

        websocket.send_json(
            {
                "type": "input",
                "seq": 3,
                "payload": {
                    "input_seq": 11,
                    "turn": "right",
                    "fast": False,
                    "fire": False,
                },
            }
        )
        event_right = _receive_until_type(websocket, "event")
        assert event_right["type"] == "event"
        assert event_right["payload"]["event_type"] == "input_accepted"
        assert event_right["payload"]["data"] == {
            "input_seq": 11,
            "turn": "right",
            "fast": False,
            "fire": False,
        }
        snapshot_after_right = _receive_until_type(websocket, "snapshot")
        assert snapshot_after_right["type"] == "snapshot"
        assert snapshot_after_right["payload"]["player"]["x"] == 500.0


def test_ws_input_defaults_to_slow_and_no_fire(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        join_ack = _receive_until_type(websocket, "join_ack")
        assert join_ack["type"] == "join_ack"
        snapshot = _receive_until_type(websocket, "snapshot")
        assert snapshot["type"] == "snapshot"

        websocket.send_json(
            {
                "type": "input",
                "seq": 2,
                "payload": {
                    "input_seq": 21,
                },
            }
        )
        event = _receive_until_type(websocket, "event")
        assert event["type"] == "event"
        assert event["payload"]["event_type"] == "input_accepted"
        assert event["payload"]["data"] == {
            "input_seq": 21,
            "turn": None,
            "fast": False,
            "fire": False,
        }
        snapshot_after_input = _receive_until_type(websocket, "snapshot")
        assert snapshot_after_input["type"] == "snapshot"
        assert snapshot_after_input["payload"]["player"]["x"] == 500.0


def test_ws_input_rejects_invalid_turn(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        join_ack = _receive_until_type(websocket, "join_ack")
        assert join_ack["type"] == "join_ack"
        snapshot = _receive_until_type(websocket, "snapshot")
        assert snapshot["type"] == "snapshot"

        websocket.send_json(
            {
                "type": "input",
                "seq": 2,
                "payload": {
                    "turn": "up",
                },
            }
        )
        error = _receive_until_type(websocket, "error")
        assert error["type"] == "error"
        assert error["payload"]["code"] == "INVALID_INPUT"


def test_ws_input_without_input_seq_is_accepted(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        _receive_until_type(websocket, "snapshot")

        websocket.send_json(
            {
                "type": "input",
                "seq": 9,
                "payload": {
                    "turn": "left",
                },
            }
        )
        event = _receive_until_type(websocket, "event")
        assert event["payload"]["event_type"] == "input_accepted"
        assert event["payload"]["data"]["input_seq"] == 9


def test_ws_keydown_hold_then_keyup_stops_movement(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        initial_snapshot = _receive_until_type(websocket, "snapshot")
        initial_x = initial_snapshot["payload"]["player"]["x"]

        websocket.send_json(
            {
                "type": "keydown",
                "seq": 2,
                "payload": {
                    "key": "ArrowLeft",
                },
            }
        )
        keydown_event = _receive_until_type(websocket, "event")
        assert keydown_event["payload"]["event_type"] == "input_accepted"
        assert keydown_event["payload"]["data"]["key_event"] == "keydown"
        assert keydown_event["payload"]["data"]["key"] == "left"

        moved_left = False
        last_x = initial_x
        for _ in range(12):
            snapshot = _receive_until_type(websocket, "snapshot")
            x = snapshot["payload"]["player"]["x"]
            if x < initial_x:
                moved_left = True
            last_x = x

        assert moved_left

        websocket.send_json(
            {
                "type": "keyup",
                "seq": 3,
                "payload": {
                    "key": "ArrowLeft",
                },
            }
        )
        keyup_event = _receive_until_type(websocket, "event")
        assert keyup_event["payload"]["event_type"] == "input_accepted"
        assert keyup_event["payload"]["data"]["key_event"] == "keyup"
        assert keyup_event["payload"]["data"]["key"] == "left"

        # Capture the first snapshot AFTER keyup was confirmed processed — that's
        # the stable reference position (an in-flight tick may have moved slightly).
        stable_snapshot = _receive_until_type(websocket, "snapshot")
        stable_x = stable_snapshot["payload"]["player"]["x"]
        for _ in range(3):
            snapshot = _receive_until_type(websocket, "snapshot")
            assert snapshot["payload"]["player"]["x"] == stable_x


def test_ws_keydown_rejects_invalid_key(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        _receive_until_type(websocket, "snapshot")

        websocket.send_json(
            {
                "type": "keydown",
                "seq": 2,
                "payload": {
                    "key": "A",
                },
            }
        )
        error = _receive_until_type(websocket, "error")
        assert error["payload"]["code"] == "INVALID_INPUT"


def test_missile_cooldown_prevents_rapid_fire():
    from riverraid.application.session_runtime import SessionRuntime
    from riverraid.application.session_entities import Plane

    runtime = SessionRuntime()
    g = runtime.new_state()
    g.plane_state = Plane.from_dict(runtime._initial_plane_state())

    fire_input = {"input_seq": 1, "turn": None, "fast": False, "fire": True}

    # First shot at t=0 should succeed
    g.game_time = 0.0
    g.last_fired_time = -999.0
    runtime.process_input(g, {**fire_input, "input_seq": 1})
    assert len(g.missiles) == 1

    # Second shot at t=0.1 (within cooldown) must be suppressed
    g.game_time = 0.1
    runtime.process_input(g, {**fire_input, "input_seq": 2})
    assert len(g.missiles) == 1

    # Shot at exactly the cooldown boundary must succeed
    g.game_time = g.last_fired_time + runtime._missile_cooldown_seconds
    runtime.process_input(g, {**fire_input, "input_seq": 3})
    assert len(g.missiles) == 2


def test_missile_expires_after_lifetime():
    from riverraid.application.session_runtime import SessionRuntime
    from riverraid.application.session_entities import Missile, Plane

    runtime = SessionRuntime()
    g = runtime.new_state()
    g.plane_state = Plane.from_dict(runtime._initial_plane_state())

    # Fire at t=0
    g.game_time = 0.0
    g.last_fired_time = -999.0
    fire_input = {"input_seq": 1, "turn": None, "fast": False, "fire": True}
    runtime.process_input(g, fire_input)
    assert len(g.missiles) == 1
    fired_at = g.missiles[0].fired_at

    # Just before lifetime ends: missile must still exist
    g.game_time = fired_at + runtime._missile_lifetime_seconds - 0.01
    g.missiles = [m for m in g.missiles if g.game_time - m.fired_at <= runtime._missile_lifetime_seconds]
    assert len(g.missiles) == 1

    # Just after lifetime ends: missile must be gone
    g.game_time = fired_at + runtime._missile_lifetime_seconds + 0.01
    g.missiles = [m for m in g.missiles if g.game_time - m.fired_at <= runtime._missile_lifetime_seconds]
    assert len(g.missiles) == 0


def test_ws_scrolls_without_input(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        first_snapshot = _receive_until_type(websocket, "snapshot")
        second_snapshot = _receive_until_type(websocket, "snapshot")

        assert second_snapshot["payload"]["camera_y"] >= first_snapshot["payload"]["camera_y"]


def test_ws_fuel_decreases_over_time(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        first_snapshot = _receive_until_type(websocket, "snapshot")
        first_fuel = first_snapshot["payload"]["hud"]["fuel"]

        lower_fuel_seen = False
        for _ in range(15):
            snapshot = _receive_until_type(websocket, "snapshot")
            if snapshot["payload"]["hud"]["fuel"] < first_fuel:
                lower_fuel_seen = True
                break

        assert lower_fuel_seen


def test_ws_collision_with_bank_emits_event(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        _receive_until_type(websocket, "snapshot")

        found_collision = False
        for index in range(30):
            websocket.send_json(
                {
                    "type": "input",
                    "seq": index + 2,
                    "payload": {
                        "input_seq": index + 1,
                        "turn": "left",
                    },
                }
            )

            for _ in range(4):
                message = websocket.receive_json()
                if message.get("type") == "event" and message.get("payload", {}).get("event_type") == "collision_bank":
                    found_collision = True
                    assert message["payload"]["data"]["hp"] <= 2
                    break
            if found_collision:
                break

        assert found_collision


def test_ws_snapshot_hud_matches_player_hp(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        _receive_until_type(websocket, "snapshot")

        latest_snapshot = None
        for index in range(30):
            websocket.send_json(
                {
                    "type": "input",
                    "seq": index + 2,
                    "payload": {
                        "turn": "left",
                    },
                }
            )

            for _ in range(5):
                message = websocket.receive_json()
                if message.get("type") == "snapshot":
                    latest_snapshot = message
                if message.get("type") == "event" and message.get("payload", {}).get("event_type") == "collision_bank":
                    break

            if latest_snapshot and latest_snapshot["payload"]["hud"]["lives"] < 3:
                break

        assert latest_snapshot is not None
        assert latest_snapshot["payload"]["hud"]["lives"] == latest_snapshot["payload"]["player"]["hp"]


def test_ws_game_over_and_restart_flow(client):
    token = _login(client)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "join", "seq": 1, "payload": {"access_token": token}})
        _receive_until_type(websocket, "join_ack")
        _receive_until_type(websocket, "snapshot")

        got_game_over = False
        for index in range(220):
            websocket.send_json(
                {
                    "type": "input",
                    "seq": index + 2,
                    "payload": {
                        "turn": "left",
                    },
                }
            )
            for _ in range(8):
                message = websocket.receive_json()
                if message.get("type") == "event" and message.get("payload", {}).get("event_type") == "game_over":
                    got_game_over = True
                    break
            if got_game_over:
                break

        assert got_game_over

        websocket.send_json(
            {
                "type": "input",
                "seq": 500,
                "payload": {
                    "turn": "right",
                },
            }
        )
        game_over_error = _receive_until_type(websocket, "error")
        assert game_over_error["payload"]["code"] == "GAME_OVER"

        websocket.send_json(
            {
                "type": "restart",
                "seq": 501,
                "payload": {},
            }
        )
        restarted_event = _receive_until_type(websocket, "event")
        assert restarted_event["payload"]["event_type"] == "game_restarted"

        restarted_snapshot = _receive_until_type(websocket, "snapshot")
        assert restarted_snapshot["payload"]["hud"]["lives"] == 3
        assert restarted_snapshot["payload"]["hud"]["level"] == 1


def test_fuel_crash_helper_reduces_life_and_resets_fuel():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["fuel"] = 1.0

    event = gateway._apply_fuel_burn_and_crash(plane_state=plane_state, elapsed_seconds=1.0)
    assert event is not None
    assert event["event_type"] == "crash_fuel"
    assert plane_state["hp"] == 2
    assert plane_state["fuel"] == 100.0


def test_bank_collision_respawn_refills_fuel():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["x"] = 0.0
    plane_state["fuel"] = 37.0
    river_banks = [{"y": plane_state["y"], "left_x": 200.0, "right_x": 800.0}]

    event = gateway._handle_bank_collision(plane_state=plane_state, river_banks=river_banks)
    assert event is not None
    assert event["event_type"] == "collision_bank"
    assert plane_state["hp"] == 2
    assert plane_state["fuel"] == 100.0


def test_fuel_station_spacing_and_size_rules():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    river_banks = [{"y": y, "left_x": 200.0, "right_x": 800.0} for y in range(0, 6001, 40)]

    fuel_stations, _, _ = gateway._ensure_fuel_stations_until(
        fuel_stations=[],
        next_station_id=1,
        next_eligible_y=0.0,
        river_banks=river_banks,
        target_y=5000.0,
    )

    assert len(fuel_stations) > 2
    for station in fuel_stations:
        assert station["width"] == gateway._plane_width
        assert station["height"] == gateway._plane_width * gateway._fuel_station_letter_count

    for index in range(1, len(fuel_stations)):
        spacing = fuel_stations[index]["y"] - fuel_stations[index - 1]["y"]
        assert spacing >= gateway._fuel_station_min_spacing


def test_refuel_rate_is_25_percent_per_second():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["fuel"] = 10.0
    station = {
        "id": "fuel_1",
        "x": plane_state["x"],
        "y": plane_state["y"] - 10,
        "width": gateway._plane_width,
        "height": gateway._plane_width * gateway._fuel_station_letter_count,
    }

    gateway._apply_refuel_from_stations(plane_state=plane_state, fuel_stations=[station], elapsed_seconds=1.0)
    assert plane_state["fuel"] == 30.0


def test_bridge_generation_interval_and_width_constraints():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    bridge_center = gateway._world_width / 2
    half_narrow_max = gateway._bridge_narrow_max / 2
    river_banks = [
        {
            "y": float(y),
            "left_x": bridge_center - half_narrow_max,
            "right_x": bridge_center + half_narrow_max,
        }
        for y in range(0, int(gateway._bridge_interval_y * 3) + 1, int(gateway._segment_height))
    ]

    bridges, next_bridge_id, next_bridge_y = gateway._ensure_bridges_until(
        bridges=[],
        next_bridge_y=gateway._bridge_interval_y,
        next_bridge_id=1,
        river_banks=river_banks,
        target_y=gateway._bridge_interval_y * 2.5,
    )

    assert len(bridges) == 2
    assert bridges[0]["y"] == gateway._bridge_interval_y
    assert bridges[1]["y"] == gateway._bridge_interval_y * 2
    for bridge in bridges:
        assert gateway._bridge_narrow_min <= bridge["width"] <= gateway._bridge_narrow_max
    assert next_bridge_id == 3
    assert next_bridge_y == gateway._bridge_interval_y * 3


def test_bridge_collision_respawns_plane_and_refills_fuel():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["x"] = 500.0
    plane_state["y"] = 100.0
    plane_state["fuel"] = 12.0

    bridges = [
        {
            "id": "bridge_1",
            "x": 500.0,
            "y": 90.0,
            "left_x": 450.0,
            "right_x": 550.0,
            "width": 100.0,
            "height": gateway._bridge_height,
        }
    ]

    event = gateway._handle_bridge_collision(plane_state=plane_state, bridges=bridges)
    assert event is not None
    assert event["event_type"] == "collision_bridge"
    assert plane_state["hp"] == 2
    assert plane_state["x"] == gateway._world_width / 2
    assert plane_state["fuel"] == gateway._fuel_capacity


def test_missile_destroys_bridge_and_adds_20_score():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["score"] = 0

    missile = {
        "id": "missile_1",
        "x": 500.0,
        "y": 100.0,
        "width": gateway._missile_width,
        "height": gateway._missile_height,
    }
    bridges = [
        {
            "id": "bridge_1",
            "x": 500.0,
            "y": 130.0,
            "left_x": 470.0,
            "right_x": 530.0,
            "width": 60.0,
            "height": gateway._bridge_height,
        }
    ]

    missiles_after = gateway._advance_missiles_and_check_collisions(
        missiles=[missile],
        fuel_stations=[],
        bridges=bridges,
        plane_state=plane_state,
        elapsed_seconds=0.09,  # Missile travels 27 units (300 * 0.09), from y=100 to y=127
    )

    assert missiles_after == []
    assert len(bridges) == 1
    assert bridges[0]["destroyed"] is True
    assert plane_state["score"] == 20


def test_destroyed_bridge_emitted_as_road_entity():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    bridge = {
        "id": "bridge_1",
        "x": 500.0,
        "y": 100.0,
        "left_x": 470.0,
        "right_x": 530.0,
        "width": 60.0,
        "height": gateway._bridge_height,
        "destroyed": True,
    }

    entities = gateway._all_entities_in_view(
        fuel_stations=[],
        missiles=[],
        bridges=[bridge],
        camera_y=0.0,
    )

    assert len(entities) == 1
    assert entities[0]["kind"] == "road"


def test_destroyed_bridge_does_not_cause_collision():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["x"] = 500.0
    plane_state["y"] = 100.0

    bridges = [
        {
            "id": "bridge_1",
            "x": 500.0,
            "y": 90.0,
            "left_x": 450.0,
            "right_x": 550.0,
            "width": 100.0,
            "height": gateway._bridge_height,
            "destroyed": True,
        }
    ]

    event = gateway._handle_bridge_collision(plane_state=plane_state, bridges=bridges)
    assert event is None


def test_all_entities_in_view_includes_bridge_entities():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    entities = gateway._all_entities_in_view(
        fuel_stations=[],
        missiles=[],
        bridges=[
            {
                "id": "bridge_1",
                "x": 500.0,
                "y": 100.0,
                "left_x": 470.0,
                "right_x": 530.0,
                "width": 60.0,
                "height": gateway._bridge_height,
            }
        ],
        camera_y=0.0,
    )

    assert len(entities) == 1
    assert entities[0]["kind"] == "bridge"
    assert entities[0]["left_x"] == 470.0
    assert entities[0]["right_x"] == 530.0


def test_prune_old_banks_keeps_previous_section_until_next_bridge_crossed():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    interval = gateway._bridge_interval_y
    river_banks = [
        {"y": float(y), "left_x": 200.0, "right_x": 800.0}
        for y in range(0, int(interval * 4) + 1, int(gateway._segment_height))
    ]

    before_second_bridge_cross = gateway._prune_old_banks(
        river_banks=river_banks,
        camera_y=(2.0 * interval) + gateway._bridge_height - 1.0,
    )
    assert min(segment["y"] for segment in before_second_bridge_cross) == 0.0

    after_second_bridge_cross = gateway._prune_old_banks(
        river_banks=river_banks,
        camera_y=(2.0 * interval) + gateway._bridge_height + 1.0,
    )
    assert min(segment["y"] for segment in after_second_bridge_cross) >= interval


def test_respawn_camera_y_returns_zero_before_first_bridge():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    assert gateway._respawn_camera_y(None) == 0.0


def test_respawn_camera_y_is_just_past_last_crossed_bridge():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    bridge_y = gateway._bridge_interval_y
    assert gateway._respawn_camera_y(bridge_y) == bridge_y + gateway._bridge_height


def test_bank_collision_respawn_includes_respawn_camera_y_in_event_data():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["x"] = 0.0  # force collision (outside banks)
    river_banks = [{"y": plane_state["y"], "left_x": 200.0, "right_x": 800.0}]

    event = gateway._handle_bank_collision(plane_state=plane_state, river_banks=river_banks)
    assert event is not None

    # Simulate what the gateway loop does after a non-fatal crash
    respawn_camera_y = gateway._respawn_camera_y(None)
    event["data"]["respawn_camera_y"] = round(respawn_camera_y, 2)

    assert event["data"]["respawn_camera_y"] == 0.0


def test_bank_collision_respawn_after_bridge_crossed():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["x"] = 0.0
    river_banks = [{"y": plane_state["y"], "left_x": 200.0, "right_x": 800.0}]

    event = gateway._handle_bank_collision(plane_state=plane_state, river_banks=river_banks)
    assert event is not None

    last_crossed_bridge_y = gateway._bridge_interval_y
    respawn_camera_y = gateway._respawn_camera_y(last_crossed_bridge_y)
    event["data"]["respawn_camera_y"] = round(respawn_camera_y, 2)

    assert event["data"]["respawn_camera_y"] == gateway._bridge_interval_y + gateway._bridge_height


def test_snapshot_payload_uses_level_parameter_for_hud():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()

    snapshot = gateway._snapshot_payload(
        tick=1,
        last_processed_input_seq=1,
        plane_state=plane_state,
        river_banks=[],
        entities=[],
        camera_y=0.0,
        level=4,
    )

    assert snapshot["hud"]["level"] == 4


def test_ensure_helicopters_until_spawns_helicopters():
    random.seed(100)  # Use a seed that produces multiple helicopters
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    bridge_center = gateway._world_width / 2
    river_banks = [
        {
            "y": float(i * gateway._segment_height),
            "left_x": bridge_center - gateway._river_max_width / 2,
            "right_x": bridge_center + gateway._river_max_width / 2,
        }
        for i in range(0, int(gateway._helicopter_min_spacing * 3) + 1, 1)
    ]

    helicopters, next_id, next_y = gateway._ensure_helicopters_until(
        helicopters=[],
        next_helicopter_id=1,
        next_helicopter_y=0.0,
        river_banks=river_banks,
        target_y=gateway._helicopter_min_spacing * 3,  # Increase target to spawn more
    )

    assert len(helicopters) >= 2
    assert next_id >= 3
    for heli in helicopters:
        assert heli["width"] == gateway._helicopter_width
        assert heli["height"] == gateway._helicopter_height
        assert heli["speed"] == gateway._helicopter_speed
        assert heli["direction"] in [1, -1]


def test_helicopters_alternate_spawn_sides():
    random.seed(123)  # Use a different seed to get mixed directions
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    bridge_center = gateway._world_width / 2
    river_banks = [
        {
            "y": float(i),
            "left_x": bridge_center - gateway._river_max_width / 2,
            "right_x": bridge_center + gateway._river_max_width / 2,
        }
        for i in range(0, int(gateway._helicopter_min_spacing * 4), 10)
    ]

    helicopters = []
    next_id = 1
    next_y = 0.0
    for _ in range(4):
        helicopters, next_id, next_y = gateway._ensure_helicopters_until(
            helicopters=helicopters,
            next_helicopter_id=next_id,
            next_helicopter_y=next_y,
            river_banks=river_banks,
            target_y=next_y + gateway._helicopter_min_spacing,
        )

    # Check that we got multiple helicopters with different starting sides
    directions = [h["direction"] for h in helicopters]
    assert 1 in directions and -1 in directions


def test_advance_helicopters_moves_side_to_side():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    heli = {
        "id": "heli_1",
        "x": 400.0,
        "y": 100.0,
        "width": gateway._helicopter_width,
        "height": gateway._helicopter_height,
        "speed": gateway._helicopter_speed,
        "direction": 1,
        "left_bound": 300.0,
        "right_bound": 700.0,
    }

    gateway._advance_helicopters(helicopters=[heli], elapsed_seconds=0.1)

    assert heli["x"] > 400.0
    assert heli["direction"] == 1


def test_helicopter_bounces_at_boundary():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    heli = {
        "id": "heli_1",
        "x": 695.0,
        "y": 100.0,
        "width": gateway._helicopter_width,
        "height": gateway._helicopter_height,
        "speed": gateway._helicopter_speed,
        "direction": 1,
        "left_bound": 300.0,
        "right_bound": 700.0,
    }

    gateway._advance_helicopters(helicopters=[heli], elapsed_seconds=1.0)

    assert heli["direction"] == -1
    assert heli["x"] == 700.0


def test_missile_destroys_helicopter_adds_10_score():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["score"] = 0

    missile = {
        "id": "missile_1",
        "x": 500.0,
        "y": 100.0,
        "width": gateway._missile_width,
        "height": gateway._missile_height,
    }
    helicopters = [
        {
            "id": "heli_1",
            "x": 500.0,
            "y": 130.0,
            "width": gateway._helicopter_width,
            "height": gateway._helicopter_height,
            "speed": 60.0,
            "direction": 1,
            "left_bound": 400.0,
            "right_bound": 600.0,
        }
    ]

    missiles_after = gateway._advance_missiles_and_check_collisions(
        missiles=[missile],
        fuel_stations=[],
        bridges=[],
        helicopters=helicopters,
        plane_state=plane_state,
        elapsed_seconds=0.09,  # Missile travels 27 units (300 * 0.09), from y=100 to y=127
    )

    assert len(missiles_after) == 0
    assert len(helicopters) == 1
    assert helicopters[0]["destroyed"] is True
    assert plane_state["score"] == 10


def test_plane_collision_with_helicopter_causes_damage():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    plane_state = gateway._initial_plane_state()
    plane_state["x"] = 500.0
    plane_state["y"] = 100.0
    plane_state["hp"] = 3

    helicopters = [
        {
            "id": "heli_1",
            "x": 500.0,
            "y": 90.0,
            "width": gateway._helicopter_width,
            "height": gateway._helicopter_height,
            "speed": 60.0,
            "direction": 1,
            "left_bound": 400.0,
            "right_bound": 600.0,
        }
    ]

    event = gateway._handle_helicopter_collision(plane_state=plane_state, helicopters=helicopters)

    assert event is not None
    assert event["event_type"] == "collision_helicopter"
    assert plane_state["hp"] == 2
    assert helicopters[0]["destroyed"] is True


def test_destroyed_helicopter_not_in_entities():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    helicopter = {
        "id": "heli_1",
        "x": 500.0,
        "y": 100.0,
        "width": gateway._helicopter_width,
        "height": gateway._helicopter_height,
        "speed": 60.0,
        "direction": 1,
        "left_bound": 400.0,
        "right_bound": 600.0,
        "destroyed": True,
    }

    entities = gateway._all_entities_in_view(
        fuel_stations=[],
        missiles=[],
        bridges=[],
        helicopters=[helicopter],
        camera_y=0.0,
    )

    assert len(entities) == 0


def test_helicopter_emitted_in_entities_when_in_view():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    helicopter = {
        "id": "heli_1",
        "x": 500.0,
        "y": 100.0,
        "width": gateway._helicopter_width,
        "height": gateway._helicopter_height,
        "speed": 60.0,
        "direction": 1,
        "left_bound": 400.0,
        "right_bound": 600.0,
    }

    entities = gateway._all_entities_in_view(
        fuel_stations=[],
        missiles=[],
        bridges=[],
        helicopters=[helicopter],
        camera_y=0.0,
    )

    assert len(entities) == 1
    assert entities[0]["kind"] == "helicopter"
    assert entities[0]["id"] == "heli_1"


def test_prune_old_helicopters():
    gateway = WebSocketGateway(validate_join_token=None)  # type: ignore[arg-type]
    helicopters = [
        {
            "id": "heli_1",
            "x": 500.0,
            "y": 50.0,
            "width": gateway._helicopter_width,
            "height": gateway._helicopter_height,
            "speed": 60.0,
            "direction": 1,
            "left_bound": 400.0,
            "right_bound": 600.0,
        },
        {
            "id": "heli_2",
            "x": 500.0,
            "y": 2000.0,
            "width": gateway._helicopter_width,
            "height": gateway._helicopter_height,
            "speed": 60.0,
            "direction": -1,
            "left_bound": 400.0,
            "right_bound": 600.0,
        },
    ]

    # Prune with camera at 500, should keep heli_2 (y=2000) but pruning checks min_y = camera_y - height
    pruned = gateway._prune_old_helicopters(
        helicopters=helicopters,
        camera_y=1500.0,
    )

    assert len(pruned) == 1
    assert pruned[0]["id"] == "heli_2"


# ── Tank tests ────────────────────────────────────────────────────────────────

def test_tank_missile_hits_plane():
    from riverraid.application.game_session_service import GameSessionService
    from riverraid.infrastructure.game_config import load_game_config

    cfg = load_game_config()
    service = GameSessionService(cfg=cfg)
    plane_state = service.initial_plane_state()
    hp_before = plane_state["hp"]

    # Place a tank missile directly overlapping the plane
    tank_missiles = [{
        "id": "tank_missile_1",
        "x": plane_state["x"],
        "y": plane_state["y"],
        "width": cfg.tank_missile_width,
        "height": cfg.tank_missile_height,
        "vx": cfg.tank_missile_speed_x,
        "fired_at": 0.0,
    }]

    event = service.handle_tank_missile_collision(plane_state=plane_state, tank_missiles=tank_missiles)

    assert event is not None
    assert event["event_type"] == "collision_tank_missile"
    assert plane_state["hp"] == hp_before - 1
    assert len(tank_missiles) == 0  # consumed missile


def test_tank_missile_misses_plane():
    from riverraid.application.game_session_service import GameSessionService
    from riverraid.infrastructure.game_config import load_game_config

    cfg = load_game_config()
    service = GameSessionService(cfg=cfg)
    plane_state = service.initial_plane_state()

    # Place a tank missile far to the side — no overlap
    tank_missiles = [{
        "id": "tank_missile_1",
        "x": 0.0,
        "y": plane_state["y"] + 500.0,
        "width": cfg.tank_missile_width,
        "height": cfg.tank_missile_height,
        "vx": cfg.tank_missile_speed_x,
        "fired_at": 0.0,
    }]

    event = service.handle_tank_missile_collision(plane_state=plane_state, tank_missiles=tank_missiles)

    assert event is None
    assert len(tank_missiles) == 1  # missile not consumed


def test_player_missile_destroys_tank():
    from riverraid.application.game_session_service import GameSessionService
    from riverraid.infrastructure.game_config import load_game_config

    cfg = load_game_config()
    service = GameSessionService(cfg=cfg)
    plane_state = service.initial_plane_state()
    plane_state["score"] = 0

    tank = {
        "id": "tank_1",
        "x": 500.0,
        "y": 300.0,
        "width": cfg.tank_width,
        "height": cfg.tank_height,
        "side": "right",
        "last_shot_at": 0.0,
        "destroyed": False,
    }
    # Missile starts just below the tank and travels upward
    missile = {
        "id": "missile_1",
        "x": 500.0,
        "y": 295.0,
        "width": cfg.missile_width,
        "height": cfg.missile_height,
        "vx": 0.0,
        "fired_at": 0.0,
    }

    tanks = [tank]
    missiles_after = service.advance_missiles_and_check_collisions(
        missiles=[missile],
        fuel_stations=[],
        bridges=[],
        helicopters=[],
        tanks=tanks,
        plane_state=plane_state,
        elapsed_seconds=0.02,  # missile travels 6 units — overlaps the tank at y=300
    )

    assert tanks[0]["destroyed"] is True
    assert plane_state["score"] == cfg.tank_score
    assert missiles_after == []  # missile consumed


def test_friendly_missile_does_not_damage_plane():
    from riverraid.application.game_session_service import GameSessionService
    from riverraid.infrastructure.game_config import load_game_config

    cfg = load_game_config()
    service = GameSessionService(cfg=cfg)

    plane_state = service.initial_plane_state()
    plane_state["x"] = 500.0
    plane_state["y"] = 60.0
    plane_state["hp"] = 3

    missile = {
        "id": "missile_1",
        "x": 500.0,
        "y": 60.0,
        "width": cfg.missile_width,
        "height": cfg.missile_height,
        "vx": 0.0,
        "fired_at": 0.0,
    }

    missiles_after = service.advance_missiles_and_check_collisions(
        missiles=[missile],
        fuel_stations=[],
        bridges=[],
        helicopters=[],
        tanks=[],
        plane_state=plane_state,
        elapsed_seconds=0.0,
    )

    assert plane_state["hp"] == 3
    assert len(missiles_after) == 1


def test_tank_fires_after_interval():
    from riverraid.application.game_session_service import GameSessionService
    from riverraid.infrastructure.game_config import load_game_config

    cfg = load_game_config()
    service = GameSessionService(cfg=cfg)

    tank = {
        "id": "tank_1",
        "x": 50.0,
        "y": 200.0,
        "width": cfg.tank_width,
        "height": cfg.tank_height,
        "side": "left",
        "last_shot_at": -(cfg.tank_shoot_interval_seconds),
        "destroyed": False,
    }

    # First call — tank is ready to fire
    new_missiles, next_id = service.maybe_fire_from_tanks(tanks=[tank], game_time=0.0, next_tank_missile_id=1)
    assert len(new_missiles) == 1
    assert new_missiles[0]["vx"] == cfg.tank_missile_speed_x  # fires to the right (left-bank tank)
    assert next_id == 2

    # Immediate second call — cooldown not elapsed
    new_missiles2, _ = service.maybe_fire_from_tanks(tanks=[tank], game_time=0.0, next_tank_missile_id=2)
    assert len(new_missiles2) == 0

    # After the interval — fires again
    new_missiles3, _ = service.maybe_fire_from_tanks(
        tanks=[tank], game_time=cfg.tank_shoot_interval_seconds, next_tank_missile_id=2
    )
    assert len(new_missiles3) == 1
