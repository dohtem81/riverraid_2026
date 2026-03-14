DEMO_SCRIPT = """
const statusEl = document.getElementById('status');
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const restartBtn = document.getElementById('restart');
const hudLivesEl = document.getElementById('hud-lives');
const hudScoreEl = document.getElementById('hud-score');
const hudLevelEl = document.getElementById('hud-level');
const hudFuelBarEl = document.getElementById('hud-fuel-bar');
let worldWidth = 1000;
let viewportHeight = 600;
let plane = null;
let riverBanks = [];
let entities = [];
let cameraY = 0;
let ws = null;
let inputSeq = 0;
let isGameOver = false;
const pressedKeys = new Set();

restartBtn.disabled = true;

function setStatus(text) {
    statusEl.textContent = text;
}

function worldToCanvas(x, y) {
    const scale = canvas.width / worldWidth;
    return { x: x * scale, y: canvas.height - ((y - cameraY) * scale) };
}

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    renderRiverBanks();
    renderEntities();
    if (!plane) {
        requestAnimationFrame(render);
        return;
    }

    const p = worldToCanvas(plane.x, plane.y);
    ctx.save();
    ctx.translate(p.x, p.y);

    // Swept-back wings
    ctx.fillStyle = '#d4b820';
    ctx.beginPath();
    ctx.moveTo(-4, 1);
    ctx.lineTo(-16, 9);
    ctx.lineTo(-11, 13);
    ctx.lineTo(0, 9);
    ctx.lineTo(11, 13);
    ctx.lineTo(16, 9);
    ctx.lineTo(4, 1);
    ctx.closePath();
    ctx.fill();

    // Tail fins
    ctx.beginPath();
    ctx.moveTo(-2, 7);
    ctx.lineTo(-8, 15);
    ctx.lineTo(-2, 11);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(2, 7);
    ctx.lineTo(8, 15);
    ctx.lineTo(2, 11);
    ctx.closePath();
    ctx.fill();

    // Fuselage
    ctx.fillStyle = '#f0d030';
    ctx.beginPath();
    ctx.moveTo(0, -16);
    ctx.lineTo(4, -4);
    ctx.lineTo(4, 7);
    ctx.lineTo(0, 12);
    ctx.lineTo(-4, 7);
    ctx.lineTo(-4, -4);
    ctx.closePath();
    ctx.fill();

    // Cockpit window
    ctx.fillStyle = '#a0d8ef';
    ctx.beginPath();
    ctx.ellipse(0, -6, 2, 4, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();

    renderGameOverOverlay();

    requestAnimationFrame(render);
}

function renderGameOverOverlay() {
    if (!isGameOver) {
        return;
    }

    ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 36px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('GAME OVER', canvas.width / 2, (canvas.height / 2) - 10);
    ctx.font = '18px Arial';
    ctx.fillText('Click Restart to play again', canvas.width / 2, (canvas.height / 2) + 24);
    ctx.textAlign = 'start';
}

function renderRiverBanks() {
    if (!riverBanks || riverBanks.length < 2) {
        return;
    }

    const scale = canvas.width / worldWidth;
    const viewportTop = cameraY;

    ctx.fillStyle = '#2d7f3b';
    for (let i = 0; i < riverBanks.length - 1; i += 1) {
        const a = riverBanks[i];
        const b = riverBanks[i + 1];

        const ay = canvas.height - ((a.y - viewportTop) * scale);
        const by = canvas.height - ((b.y - viewportTop) * scale);
        if ((ay < 0 && by < 0) || (ay > canvas.height && by > canvas.height)) {
            continue;
        }

        const aLeft = a.left_x * scale;
        const bLeft = b.left_x * scale;
        const aRight = a.right_x * scale;
        const bRight = b.right_x * scale;

        ctx.beginPath();
        ctx.moveTo(0, ay);
        ctx.lineTo(aLeft, ay);
        ctx.lineTo(bLeft, by);
        ctx.lineTo(0, by);
        ctx.closePath();
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(aRight, ay);
        ctx.lineTo(canvas.width, ay);
        ctx.lineTo(canvas.width, by);
        ctx.lineTo(bRight, by);
        ctx.closePath();
        ctx.fill();
    }
}

function renderEntities() {
    if (!entities || entities.length === 0) {
        return;
    }

    for (const entity of entities) {
        if (entity.kind === 'bridge' || entity.kind === 'road') {
            const scale = canvas.width / worldWidth;
            const leftPos = worldToCanvas(entity.left_x, entity.y);
            const rightPos = worldToCanvas(entity.right_x, entity.y);
            const bridgeHeightPx = Math.max(4, entity.height * scale);
            const bridgeTopY = leftPos.y - bridgeHeightPx;

            // Black road: left screen edge → left bank
            ctx.fillStyle = '#111111';
            ctx.fillRect(0, bridgeTopY, leftPos.x, bridgeHeightPx);

            // Black road: right bank → right screen edge
            ctx.fillStyle = '#111111';
            ctx.fillRect(rightPos.x, bridgeTopY, canvas.width - rightPos.x, bridgeHeightPx);

            if (entity.kind === 'bridge') {
                // Brown bridge span across the river
                const bankOverlapPx = Math.max(3, 8 * scale);
                const drawLeftX = Math.max(0, leftPos.x - bankOverlapPx);
                const drawRightX = Math.min(canvas.width, rightPos.x + bankOverlapPx);
                const drawWidth = Math.max(1, drawRightX - drawLeftX);
                ctx.fillStyle = '#8B4513';
                ctx.fillRect(drawLeftX, bridgeTopY, drawWidth, bridgeHeightPx);
                ctx.strokeStyle = '#5C2D00';
                ctx.lineWidth = 1;
                ctx.strokeRect(drawLeftX, bridgeTopY, drawWidth, bridgeHeightPx);
            }
            continue;
        }
        if (entity.kind === 'missile') {
            const scale = canvas.width / worldWidth;
            const mPos = worldToCanvas(entity.x, entity.y + entity.height);
            const mHeightPx = Math.max(2, entity.height * scale);
            const mWidthPx = Math.max(2, entity.width * scale);
            ctx.fillStyle = '#ffff66';
            ctx.fillRect(mPos.x - mWidthPx / 2, mPos.y, mWidthPx, mHeightPx);
            continue;
        }
        if (entity.kind === 'helicopter') {
            const hscale = canvas.width / worldWidth;
            const hpos = worldToCanvas(entity.x, entity.y);
            ctx.save();
            ctx.translate(hpos.x, hpos.y);
            // Tail boom
            ctx.fillStyle = '#3a7a2a';
            ctx.fillRect(10, -2, 16, 4);
            // Tail rotor
            ctx.fillStyle = '#2a6a1a';
            ctx.fillRect(24, -7, 3, 14);
            // Body
            ctx.fillStyle = '#4a8a3a';
            ctx.beginPath();
            ctx.ellipse(0, 0, 13, 8, 0, 0, Math.PI * 2);
            ctx.fill();
            // Cockpit window
            ctx.fillStyle = '#1a2e1a';
            ctx.beginPath();
            ctx.ellipse(-3, -1, 6, 5, 0, 0, Math.PI * 2);
            ctx.fill();
            // Main rotor
            ctx.strokeStyle = '#8ac870';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(-20, -10);
            ctx.lineTo(20, -10);
            ctx.stroke();
            ctx.lineWidth = 1;
            // Skids
            ctx.fillStyle = '#6aaa5a';
            ctx.fillRect(-11, 7, 22, 3);
            ctx.restore();
            continue;
        }

        if (entity.kind === 'tank') {
            const tscale = canvas.width / worldWidth;
            const tpos = worldToCanvas(entity.x, entity.y);
            const tw = Math.max(6, entity.width * tscale);
            const th = Math.max(4, entity.height * tscale);
            ctx.save();
            ctx.translate(tpos.x, tpos.y);
            // Hull
            ctx.fillStyle = '#222222';
            ctx.fillRect(-tw / 2, -th, tw, th);
            // Turret
            const turretW = tw * 0.45;
            const turretH = th * 0.55;
            ctx.fillStyle = '#111111';
            ctx.fillRect(-turretW / 2, -th - turretH * 0.6, turretW, turretH);
            // Gun barrel pointing inward (toward river)
            const barrelLen = tw * 0.55;
            const barrelDir = entity.side === 'left' ? 1 : -1;
            ctx.fillStyle = '#000000';
            ctx.fillRect(barrelDir > 0 ? 0 : -barrelLen, -th - turretH * 0.2, barrelLen, th * 0.2);
            ctx.restore();
            continue;
        }

        if (entity.kind === 'tank_missile') {
            const scale = canvas.width / worldWidth;
            const mpos = worldToCanvas(entity.x, entity.y + entity.height / 2);
            const mw = Math.max(4, entity.width * scale);
            const mh = Math.max(2, entity.height * scale);
            ctx.fillStyle = '#ff8800';
            ctx.fillRect(mpos.x - mw / 2, mpos.y - mh / 2, mw, mh);
            continue;
        }

        if (entity.kind !== 'fuel_station') {
            continue;
        }

        {
            const fscale = canvas.width / worldWidth;
            const ftop = worldToCanvas(entity.x, entity.y + entity.height);
            const stationH = entity.height * fscale;
            const stationW = entity.width * fscale;
            const fx = ftop.x - stationW / 2;
            const fy = ftop.y;
            const letters = ['F', 'U', 'E', 'L'];
            const bgColors = ['#cc1111', '#eeeeee', '#cc1111', '#eeeeee'];
            const fgColors = ['#ffffff', '#cc1111', '#ffffff', '#cc1111'];
            const cellH = stationH / 4;
            const fontSize = Math.max(8, Math.min(18, cellH * 0.72));
            ctx.font = `bold ${fontSize}px Arial`;
            ctx.textAlign = 'center';
            for (let i = 0; i < 4; i += 1) {
                const ly = fy + cellH * i;
                ctx.fillStyle = bgColors[i];
                ctx.fillRect(fx, ly, stationW, cellH);
                ctx.fillStyle = fgColors[i];
                ctx.fillText(letters[i], fx + stationW / 2, ly + cellH * 0.78);
            }
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.strokeRect(fx, fy, stationW, stationH);
            ctx.textAlign = 'start';
        }
    }
}

function updateHud(hud) {
    if (!hud) {
        return;
    }

    if (typeof hud.lives === 'number') {
        hudLivesEl.textContent = String(hud.lives);
    }
    if (typeof hud.score === 'number') {
        hudScoreEl.textContent = String(hud.score);
    }
    if (typeof hud.level === 'number') {
        hudLevelEl.textContent = String(hud.level);
    }
    if (typeof hud.fuel === 'number' && hudFuelBarEl) {
        hudFuelBarEl.style.width = Math.max(0, Math.min(100, hud.fuel)) + '%';
        const pct = hud.fuel / 100;
        const r = Math.round(212 * pct + 100 * (1 - pct));
        const g = Math.round(208 * pct + 20 * (1 - pct));
        hudFuelBarEl.style.background = `rgb(${r},${g},20)`;
    }
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
        throw new Error('Login failed');
    }

    return response.json();
}

async function connect() {
    try {
        setStatus('Logging in...');
        const auth = await login();
        setStatus('Opening websocket...');

        const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(`${scheme}://${location.host}/ws`);

        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'join',
                seq: 1,
                payload: { access_token: auth.access_token }
            }));
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'join_ack') {
                if (msg.payload && msg.payload.render_config) {
                    worldWidth = Number(msg.payload.render_config.world_width || worldWidth);
                    viewportHeight = Number(msg.payload.render_config.viewport_height || viewportHeight);
                    canvas.height = viewportHeight;
                }
                isGameOver = false;
                restartBtn.disabled = true;
                setStatus('Connected. Use Left/Right arrow keys to move, Space to fire.');
            }
            if (msg.type === 'event' && msg.payload) {
                if (msg.payload.event_type === 'game_over') {
                    isGameOver = true;
                    restartBtn.disabled = false;
                    setStatus('Game over. Click Restart.');
                }
                if (msg.payload.event_type === 'game_restarted') {
                    isGameOver = false;
                    restartBtn.disabled = true;
                    setStatus('Game restarted. Use Left/Right arrow keys to move, Space to fire.');
                }
                const crashEvents = ['collision_bank', 'collision_bridge', 'crash_fuel', 'collision_helicopter'];
                if (crashEvents.includes(msg.payload.event_type) && msg.payload.data) {
                    if (typeof msg.payload.data.respawn_camera_y === 'number') {
                        cameraY = msg.payload.data.respawn_camera_y;
                    }
                }
            }
            if (msg.type === 'snapshot' && msg.payload && msg.payload.player) {
                plane = msg.payload.player;
                updateHud(msg.payload.hud);
                if (Array.isArray(msg.payload.entities)) {
                    entities = msg.payload.entities;
                }
                if (typeof msg.payload.camera_y === 'number') {
                    cameraY = msg.payload.camera_y;
                }
                if (Array.isArray(msg.payload.river_banks)) {
                    riverBanks = msg.payload.river_banks;
                }
                setStatus(`Plane x=${plane.x}, y=${plane.y}, camera=${cameraY.toFixed(1)}`);
            }
            if (msg.type === 'error') {
                setStatus(`Error: ${msg.payload.code} - ${msg.payload.message}`);
            }
        };

        ws.onerror = () => setStatus('WebSocket error');
        ws.onclose = () => setStatus('WebSocket closed');
    } catch (err) {
        setStatus(err.message || 'Failed to connect');
    }
}

function sendKeyEvent(type, key) {
    if (!ws || ws.readyState !== WebSocket.OPEN || isGameOver) {
        return;
    }

    inputSeq += 1;
    ws.send(JSON.stringify({
        type,
        seq: inputSeq + 1,
        payload: {
            key,
        }
    }));
}

function sendRestart() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        return;
    }

    inputSeq += 1;
    ws.send(JSON.stringify({
        type: 'restart',
        seq: inputSeq + 1,
        payload: {}
    }));
}

window.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'ArrowUp' || event.key === 'ArrowDown' || event.key === ' ') {
        event.preventDefault();
        if (pressedKeys.has(event.key)) {
            return;
        }
        pressedKeys.add(event.key);
        sendKeyEvent('keydown', event.key === ' ' ? 'Space' : event.key);
    }
});

window.addEventListener('keyup', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'ArrowUp' || event.key === 'ArrowDown' || event.key === ' ') {
        event.preventDefault();
        pressedKeys.delete(event.key);
        sendKeyEvent('keyup', event.key === ' ' ? 'Space' : event.key);
    }
});

document.getElementById('connect').addEventListener('click', connect);
restartBtn.addEventListener('click', sendRestart);
render();
"""
