def test_root_serves_render_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "RiverRaid Backend Render Test" in response.text
    assert "canvas" in response.text
    assert "Enter player name" in response.text
    assert "Lives:" in response.text
    assert "Score:" in response.text
    assert "Level:" in response.text
    assert "fuel-gauge" in response.text
    assert "Connect" in response.text
    assert "Restart" in response.text


def test_games_page_served_without_main_link(client):
    games_response = client.get("/games")
    assert games_response.status_code == 200
    assert "Recorded Games" in games_response.text
    assert "/api/v1/games" in games_response.text

    root_response = client.get("/")
    assert root_response.status_code == 200
    assert "href=\"/games\"" not in root_response.text
