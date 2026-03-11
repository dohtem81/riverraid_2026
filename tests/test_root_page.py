def test_root_serves_render_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "RiverRaid Backend Render Test" in response.text
    assert "canvas" in response.text
    assert "Lives:" in response.text
    assert "Score:" in response.text
    assert "Level:" in response.text
    assert "Fuel:" in response.text
    assert "Restart" in response.text
