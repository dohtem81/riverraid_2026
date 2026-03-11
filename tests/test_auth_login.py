def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "pilot", "password": "pilot1234"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "Bearer"
    assert payload["player_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["expires_in"] == 3600
    assert isinstance(payload["access_token"], str)


def test_login_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "pilot", "password": "wrong"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["error"]["code"] == "INVALID_CREDENTIALS"
