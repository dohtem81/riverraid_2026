from riverraid.infrastructure.config_credential_provider import ConfigCredentialProvider


def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "pilot"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "Bearer"
    assert payload["player_id"] == ConfigCredentialProvider._player_id_for("pilot")
    assert payload["expires_in"] == 3600
    assert isinstance(payload["access_token"], str)


def test_login_blank_player_name(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "   "},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"]["code"] == "INVALID_PLAYER_NAME"
