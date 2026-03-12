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
.hud-fuel-gauge { display: flex; align-items: center; gap: 7px; }
.fuel-gauge-lbl { font-size: 13px; font-weight: bold; color: #f0d030; font-family: 'Courier New', monospace; line-height: 1; }
.fuel-gauge-track { position: relative; width: 130px; height: 14px; background: #060e1a; border: 2px solid #f0d030; border-radius: 2px; overflow: visible; }
.fuel-gauge-fill { height: 100%; background: #f0d030; width: 100%; border-radius: 1px; transition: width 0.15s, background 0.15s; }
.fuel-gauge-tick { position: absolute; top: -4px; left: 50%; width: 2px; height: calc(100% + 8px); background: rgba(240,208,48,0.6); pointer-events: none; }
.hud-item { color: #dce6ff; }
.hud-item strong { color: #ffffff; margin-right: 4px; }
"""
