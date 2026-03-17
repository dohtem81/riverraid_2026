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
        <input id="username" value="pilot" placeholder="Enter player name" />
        <button id="connect">Connect</button>
        <button id="restart" disabled>Restart</button>
    </div>
    <div id="status">Idle</div>
    <div class="game-area">
        <div class="game-shell">
            <canvas id="game" width="1000" height="600"></canvas>
            <div class="hud">
                <div class="hud-item"><strong>Lives:</strong><span id="hud-lives">3</span></div>
                <div class="hud-item"><strong>Score:</strong><span id="hud-score">0</span></div>
                <div class="hud-item"><strong>Level:</strong><span id="hud-level">1</span></div>
                <div class="hud-fuel-gauge">
                    <span class="fuel-gauge-lbl">E</span>
                    <div class="fuel-gauge-track">
                        <div class="fuel-gauge-fill" id="hud-fuel-bar" style="width:100%"></div>
                        <div class="fuel-gauge-tick"></div>
                    </div>
                    <span class="fuel-gauge-lbl">F</span>
                </div>
            </div>
        </div>
        <div class="leaderboard">
            <h2>&#127942; Top Scores</h2>
            <div id="leaderboard-body"><p class="empty">No scores yet</p></div>
        </div>
    </div>
    <script>{DEMO_SCRIPT}</script>
</body>
</html>
"""
