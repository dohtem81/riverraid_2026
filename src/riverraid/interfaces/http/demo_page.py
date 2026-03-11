from riverraid.interfaces.http.demo_script import DEMO_SCRIPT
from riverraid.interfaces.http.demo_style import DEMO_STYLE


INDEX_HTML = f"""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>RiverRaid Phase 0</title>
    <style>{DEMO_STYLE}</style>
</head>
<body>
    <h1>RiverRaid Backend Render Test</h1>
    <div class="row">
        <input id="username" value="pilot" />
        <input id="password" value="pilot1234" type="password" />
        <button id="connect">Login + Connect</button>
        <button id="restart" disabled>Restart</button>
    </div>
    <div id="status">Idle</div>
    <div class="game-shell">
        <canvas id="game" width="1000" height="600"></canvas>
        <div class="hud">
            <div class="hud-item"><strong>Lives:</strong><span id="hud-lives">3</span></div>
            <div class="hud-item"><strong>Score:</strong><span id="hud-score">0</span></div>
            <div class="hud-item"><strong>Level:</strong><span id="hud-level">1</span></div>
            <div class="hud-item"><strong>Fuel:</strong><span id="hud-fuel">100</span></div>
        </div>
    </div>
    <script>{DEMO_SCRIPT}</script>
</body>
</html>
"""
