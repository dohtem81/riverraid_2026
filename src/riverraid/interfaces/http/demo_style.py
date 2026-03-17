DEMO_STYLE = """
body { font-family: Arial, sans-serif; margin: 16px; background: #0b1020; color: #e8eefc; }
h1 { margin: 0 0 12px 0; font-size: 20px; }
.row { display: flex; gap: 8px; margin-bottom: 10px; }
input, button { padding: 8px; border-radius: 6px; border: 1px solid #2c3a64; }
input { background: #111a33; color: #e8eefc; }
button { background: #1f6feb; color: #fff; cursor: pointer; }
.hidden { display: none; }
#status { margin: 8px 0; color: #a9b8e8; }
canvas { background: #0a2e6f; border: 1px solid #2c3a64; }
.game-shell { width: 1000px; }
.hud { display: flex; justify-content: space-between; align-items: center; gap: 12px; background: #0d1428; border: 1px solid #2c3a64; border-top: none; padding: 8px 12px; font-size: 14px; }
.fuel-gauge-lbl { font-size: 13px; font-weight: bold; color: #f0d030; font-family: 'Courier New', monospace; line-height: 1; }
.fuel-gauge-track { position: relative; width: 130px; height: 14px; background: #060e1a; border: 2px solid #f0d030; border-radius: 2px; overflow: visible; }
.fuel-gauge-fill { height: 100%; background: #f0d030; width: 100%; border-radius: 1px; transition: width 0.15s, background 0.15s; }
.fuel-gauge-tick { position: absolute; top: -4px; left: 50%; width: 2px; height: calc(100% + 8px); background: rgba(240,208,48,0.6); pointer-events: none; }
.hud-item { color: #dce6ff; }
.hud-item strong { color: #ffffff; margin-right: 4px; }
.hud-fuel-gauge { display: flex; align-items: center; gap: 7px; }
/* leaderboard */
.game-area { display: flex; gap: 16px; align-items: flex-start; }
.leaderboard { width: 260px; background: #0d1428; border: 1px solid #2c3a64; border-radius: 6px; padding: 12px; flex-shrink: 0; }
.leaderboard h2 { margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #f0d030; text-align: center; }
.leaderboard table { width: 100%; border-collapse: collapse; font-size: 13px; }
.leaderboard th { color: #7a8eb8; font-weight: normal; padding: 2px 4px; text-align: left; border-bottom: 1px solid #1e2d50; }
.leaderboard td { padding: 4px 4px; border-bottom: 1px solid #121e38; color: #dce6ff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 80px; }
.leaderboard td.rank { color: #7a8eb8; width: 20px; text-align: right; }
.leaderboard td.score { color: #f0d030; font-weight: bold; }
.leaderboard td.level { color: #80c0ff; }
.leaderboard .empty { color: #4a5880; font-size: 12px; text-align: center; padding: 16px 0; }
"""
