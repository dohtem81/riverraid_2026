import pytest


@pytest.mark.parametrize("path", ["/api/v1/auth/register", "/api/v1/auth/refresh", "/api/v1/auth/logout"])
def test_phase0_auth_endpoints_not_implemented(client, path):
    response = client.post(path, json={})
    assert response.status_code == 501

    payload = response.json()
    assert payload["detail"]["error"]["code"] == "NOT_IMPLEMENTED_PHASE0"
