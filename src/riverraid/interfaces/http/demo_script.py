DEMO_SCRIPT = """
const statusEl = document.getElementById('status');
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const restartBtn = document.getElementById('restart');
const hudLivesEl = document.getElementById('hud-lives');
const hudScoreEl = document.getElementById('hud-score');
const hudLevelEl = document.getElementById('hud-level');
const hudFuelEl = document.getElementById('hud-fuel');
let worldWidth = 1000;
let viewportHeight = 600;
let plane = null;
let riverBanks = [];
let entities = [];
let cameraY = 0;
let ws = null;
let inputSeq = 0;
let isGameOver = false;
let lastFireTime = 0;

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
    ctx.fillStyle = '#00d4ff';
    ctx.beginPath();
    ctx.moveTo(p.x, p.y - 14);
    ctx.lineTo(p.x - 10, p.y + 10);
    ctx.lineTo(p.x + 10, p.y + 10);
    ctx.closePath();
    ctx.fill();

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
        if (entity.kind !== 'fuel_station') {
            continue;
        }

        const top = worldToCanvas(entity.x, entity.y + entity.height);
        const bottom = worldToCanvas(entity.x, entity.y);
        const stationHeightPx = Math.abs(bottom.y - top.y);

        ctx.fillStyle = '#f0d84a';
        ctx.fillRect(
            top.x - 1,
            Math.min(top.y, bottom.y),
            2,
            stationHeightPx
        );

        const letters = ['F', 'U', 'E', 'L'];
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        for (let i = 0; i < letters.length; i += 1) {
            const y = Math.min(top.y, bottom.y) + 14 + (i * 16);
            if (y > Math.max(top.y, bottom.y) - 4) {
                break;
            }
            ctx.fillText(letters[i], top.x, y);
        }
        ctx.textAlign = 'start';
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
    if (typeof hud.fuel === 'number') {
        hudFuelEl.textContent = String(hud.fuel);
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
                const crashEvents = ['collision_bank', 'collision_bridge', 'crash_fuel'];
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

function sendTurnInput(turn) {
    if (!ws || ws.readyState !== WebSocket.OPEN || isGameOver) {
        return;
    }

    inputSeq += 1;
    ws.send(JSON.stringify({
        type: 'input',
        seq: inputSeq + 1,
        payload: {
            turn,
        }
    }));
}

function sendFire() {
    if (!ws || ws.readyState !== WebSocket.OPEN || isGameOver) {
        return;
    }

    const now = Date.now();
    if (now - lastFireTime < 500) {
        return;
    }
    lastFireTime = now;

    inputSeq += 1;
    ws.send(JSON.stringify({
        type: 'input',
        seq: inputSeq + 1,
        payload: {
            fire: true,
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
    if (event.key === 'ArrowLeft') {
        event.preventDefault();
        sendTurnInput('left');
    }
    if (event.key === 'ArrowRight') {
        event.preventDefault();
        sendTurnInput('right');
    }
    if (event.key === ' ') {
        event.preventDefault();
        sendFire();
    }
});

document.getElementById('connect').addEventListener('click', connect);
restartBtn.addEventListener('click', sendRestart);
render();
"""
