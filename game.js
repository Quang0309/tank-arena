// Grid configuration
const GRID_SIZE = 24;
const CELL_PIXELS = 24; // 24 * 24 = 576 canvas size

// Cell Types
const CELL_EMPTY = 0;
const CELL_INDESTRUCTIBLE = 1;
const CELL_DESTRUCTIBLE = 2;
const CELL_BUSH = 3;
const CELL_FUEL = 4;

// Directions & vectors
const DIR_VECTORS = {
    "UP": { x: 0, y: -1 },
    "DOWN": { x: 0, y: 1 },
    "LEFT": { x: -1, y: 0 },
    "RIGHT": { x: 1, y: 0 }
};

// Game State variables
let map = [];
let turn = 0;
let maxTurns = 200;
let gameInterval = null;
let isPlaying = false;
let isPaused = false;

// Player states
let players = {
    1: {
        id: 1,
        color: '#f39c12', // Yellow
        name: 'Player 1',
        x: 0,
        y: 0,
        hp: 0,
        maxHp: 0,
        fuel: 0,
        maxFuel: 0,
        direction: 'RIGHT',
        type: 'python', // 'manual' or 'python'
        code: null,
        filename: 'No file selected',
        baseX: 0,
        baseY: 0,
        baseHp: 0,
        maxBaseHp: 0,
        history: [],
        currentAction: null, // Stored for manual input
        inBush: false,
        lastKnownX: 0,
        lastKnownY: 0
    },
    2: {
        id: 2,
        color: '#2ecc71', // Green
        name: 'Player 2',
        x: 0,
        y: 0,
        hp: 0,
        maxHp: 0,
        fuel: 0,
        maxFuel: 0,
        direction: 'LEFT',
        type: 'python', // 'manual' or 'python'
        code: null,
        filename: 'No file selected',
        baseX: 0,
        baseY: 0,
        baseHp: 0,
        maxBaseHp: 0,
        history: [],
        currentAction: null, // Stored for manual input
        inBush: false,
        lastKnownX: 0,
        lastKnownY: 0
    }
};

// Bullet tracking for visual rendering (fade out)
let bulletsFired = [];

// Pyodide variables
let pyodideInstance = null;
let p1Namespace = null;
let p2Namespace = null;

// UI Elements
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const btnStart = document.getElementById('btn-start');
const btnPause = document.getElementById('btn-pause');
const btnReset = document.getElementById('btn-reset');
const speedSlider = document.getElementById('game-speed');
const speedValText = document.getElementById('speed-val');
const loaderOverlay = document.getElementById('loader-overlay');
const logWindow = document.getElementById('log-window');

// Initialize Game
window.addEventListener('DOMContentLoaded', async () => {
    initUIControls();
    generateSymmetricMap();
    requestAnimationFrame(animationLoop);
    await initPyodideEngine();
});

function animationLoop(timestamp) {
    renderGame();
    requestAnimationFrame(animationLoop);
}

// Setup UI control listeners
function initUIControls() {
    // Player controller type changes
    document.getElementById('p1-type').addEventListener('change', (e) => {
        players[1].type = e.target.value;
        const container = document.getElementById('p1-file-input-container');
        container.style.display = e.target.value === 'python' ? 'flex' : 'none';
        logToConsole(`[SYSTEM] Player 1 control set to: ${e.target.value.toUpperCase()}`);
        resetGame();
    });

    document.getElementById('p2-type').addEventListener('change', (e) => {
        players[2].type = e.target.value;
        const container = document.getElementById('p2-file-input-container');
        container.style.display = e.target.value === 'python' ? 'flex' : 'none';
        logToConsole(`[SYSTEM] Player 2 control set to: ${e.target.value.toUpperCase()}`);
        resetGame();
    });

    // File Uploads
    document.getElementById('p1-file').addEventListener('change', (e) => {
        handleFileUpload(1, e.target.files[0]);
    });

    document.getElementById('p2-file').addEventListener('change', (e) => {
        handleFileUpload(2, e.target.files[0]);
    });

    // Speed Slider
    speedSlider.addEventListener('input', (e) => {
        speedValText.innerText = `${e.target.value}ms`;
        if (isPlaying && !isPaused && isRunningAutomatically()) {
            pauseMatchLoop();
            startMatchLoop();
        }
    });

    // Action Buttons
    btnStart.addEventListener('click', startMatch);
    btnPause.addEventListener('click', togglePause);
    btnReset.addEventListener('click', resetGame);

    // Keyboard controls for manual mode
    window.addEventListener('keydown', handleKeyDown);
}

// Check if game should tick automatically
function isRunningAutomatically() {
    return players[1].type === 'python' && players[2].type === 'python';
}

// Log message to the virtual console
function logToConsole(message, type = 'system-msg') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerText = message;
    logWindow.appendChild(entry);
    logWindow.scrollTop = logWindow.scrollHeight;
}

// File Upload reader
function handleFileUpload(playerNum, file) {
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        players[playerNum].code = e.target.result;
        players[playerNum].filename = file.name;
        document.getElementById(`p${playerNum}-filename`).innerText = file.name;
        logToConsole(`[SYSTEM] Player ${playerNum} script loaded: "${file.name}"`, 'system-msg');
        
        // Load into Pyodide namespace
        loadBotIntoNamespace(playerNum, e.target.result);
    };
    reader.readAsText(file);
}

// Initialize Pyodide
async function initPyodideEngine() {
    try {
        pyodideInstance = await loadPyodide();
        // Create custom namespaces
        p1Namespace = pyodideInstance.globals.get("dict")();
        p2Namespace = pyodideInstance.globals.get("dict")();
        
        // Redirect Python stdout/stderr to the game's System Log
        pyodideInstance.runPython(`
import sys

class GameLogWriter:
    def __init__(self):
        self.buffer = ""
    def write(self, text):
        self.buffer += text
        newline = chr(10)
        while newline in self.buffer:
            line, self.buffer = self.buffer.split(newline, 1)
            if line.strip():
                from js import document
                log_window = document.getElementById("log-window")
                entry = document.createElement("div")
                entry.className = "log-entry action-msg"
                entry.textContent = line
                log_window.appendChild(entry)
                log_window.scrollTop = log_window.scrollHeight
    def flush(self):
        pass

sys.stdout = GameLogWriter()
sys.stderr = GameLogWriter()
`);
        
        // Hide loader overlay
        loaderOverlay.style.opacity = 0;
        setTimeout(() => {
            loaderOverlay.style.display = 'none';
        }, 300);
        logToConsole("[SYSTEM] Pyodide WASM Engine initialized successfully.", 'system-msg');
    } catch (err) {
        console.error(err);
        document.querySelector('.loader-text').innerText = "ERROR LOADING PYODIDE engine!";
        logToConsole("[ERROR] Failed to load Pyodide WASM engine. See browser logs.", 'damage-msg');
    }
}

// Load Bot Code into respective Pyodide namespace
function loadBotIntoNamespace(playerNum, codeString) {
    if (!pyodideInstance) return;
    try {
        const ns = playerNum === 1 ? p1Namespace : p2Namespace;
        // Clean out previous values in namespace, preserving __builtins__
        const builtins = ns.get("__builtins__");
        ns.clear();
        if (builtins) {
            ns.set("__builtins__", builtins);
        }
        
        // Run code to load get_move into the namespace
        pyodideInstance.runPython(codeString, { globals: ns });
        
        // Check if get_move function exists
        const hasGetMove = pyodideInstance.runPython(`'get_move' in globals()`, { globals: ns });
        if (hasGetMove) {
            logToConsole(`[SYSTEM] Player ${playerNum} bot verified! "get_move(state)" found.`, 'system-msg');
        } else {
            logToConsole(`[WARNING] Player ${playerNum} script compiled, but "get_move(state)" function was not found!`, 'damage-msg');
        }
    } catch (err) {
        logToConsole(`[PYTHON ERROR P${playerNum}] Compile error:\n${err.message}`, 'damage-msg');
    }
}

// Map generation (24x24 rotationally symmetric)
function generateSymmetricMap() {
    // 0 = empty, 1 = indestructible, 2 = destructible
    map = Array(GRID_SIZE).fill(null).map(() => Array(GRID_SIZE).fill(CELL_EMPTY));
    
    // Set Bases & Tanks (Symmetrical)
    // P1 Base at (1, 11), P1 Tank starts at (1, 8) facing RIGHT
    // P2 Base at (22, 12), P2 Tank starts at (22, 15) facing LEFT
    players[1].baseX = 1;
    players[1].baseY = 11;
    
    players[2].baseX = 22;
    players[2].baseY = 12;

    players[1].x = 1;
    players[1].y = 8;
    players[1].direction = 'RIGHT';

    players[2].x = 22;
    players[2].y = 15;
    players[2].direction = 'LEFT';

    // Randomized game stats (same values for both to maintain fairness)
    const randomHp = Math.floor(Math.random() * 4) + 3; // 3 to 6
    const randomBaseHp = Math.floor(Math.random() * 6) + 5; // 5 to 10
    const randomFuel = Math.floor(Math.random() * 21) + 40; // 40 to 60

    for (let pId of [1, 2]) {
        players[pId].hp = randomHp;
        players[pId].maxHp = randomHp;
        players[pId].baseHp = randomBaseHp;
        players[pId].maxBaseHp = randomBaseHp;
        players[pId].fuel = randomFuel;
        players[pId].maxFuel = randomFuel;
        players[pId].history = [];
        players[pId].currentAction = null;
        players[pId].inBush = false;
        players[pId].lastKnownX = players[pId].x;
        players[pId].lastKnownY = players[pId].y;
    }

    // Helper function for Drunkard's Walk cluster generation
    function randomWalkCluster(startX, startY, length, cellType, canOverwriteDestructible) {
        let cx = startX;
        let cy = startY;
        const directions = [[0, -1], [0, 1], [-1, 0], [1, 0]];
        
        for (let i = 0; i < length; i++) {
            // Check boundaries (only left half of map for symmetry)
            if (cx >= 0 && cx < GRID_SIZE / 2 && cy >= 0 && cy < GRID_SIZE) {
                if (!isCloseToSpawn(cx, cy)) {
                    let placeCell = false;
                    const currentCell = map[cy][cx];
                    if (currentCell === CELL_EMPTY) {
                        placeCell = true;
                    } else if (canOverwriteDestructible && currentCell === CELL_DESTRUCTIBLE) {
                        placeCell = true;
                    }
                    
                    if (placeCell) {
                        // For walls, we randomize the type if cellType is a function, otherwise just use cellType
                        const typeToPlace = typeof cellType === 'function' ? cellType() : cellType;
                        map[cy][cx] = typeToPlace;
                        
                        // Mirror rotationally to bottom-right half
                        const symX = (GRID_SIZE - 1) - cx;
                        const symY = (GRID_SIZE - 1) - cy;
                        map[symY][symX] = typeToPlace;
                    }
                }
            }
            
            // Pick a random direction
            const dir = directions[Math.floor(Math.random() * directions.length)];
            cx += dir[0];
            cy += dir[1];
        }
    }

    // Place Walls using Random Walk Clusters
    const numWallClusters = 10 + Math.floor(Math.random() * 5); // 10 to 14 clusters per side
    for (let c = 0; c < numWallClusters; c++) {
        let sx = Math.floor(Math.random() * (GRID_SIZE / 2));
        let sy = Math.floor(Math.random() * GRID_SIZE);
        const length = 10 + Math.floor(Math.random() * 11); // 10 to 20 steps
        // 40% indestructible, 60% destructible
        randomWalkCluster(sx, sy, length, () => Math.random() < 0.4 ? CELL_INDESTRUCTIBLE : CELL_DESTRUCTIBLE, false);
    }

    // Place Bushes using Random Walk Corridors
    const numBushCorridors = 3 + Math.floor(Math.random() * 2); // 3 to 4 corridors per side
    for (let c = 0; c < numBushCorridors; c++) {
        let sx = Math.floor(Math.random() * (GRID_SIZE / 2));
        let sy = Math.floor(Math.random() * GRID_SIZE);
        const length = 8 + Math.floor(Math.random() * 8); // 8 to 15 steps
        randomWalkCluster(sx, sy, length, CELL_BUSH, true); // True to overwrite destructible walls
    }

    // Place Fuel Canisters symmetrically
    let canistersPlaced = 0;
    while(canistersPlaced < 1) { // 1 per side (2 total)
        // Try to place in the middle columns (e.g. x between 6 and 11)
        let x = 6 + Math.floor(Math.random() * 6);
        let y = Math.floor(Math.random() * GRID_SIZE);
        if (!isCloseToSpawn(x, y) && map[y][x] === CELL_EMPTY) {
            map[y][x] = CELL_FUEL;
            const symX = (GRID_SIZE - 1) - x;
            const symY = (GRID_SIZE - 1) - y;
            map[symY][symX] = CELL_FUEL;
            canistersPlaced++;
        }
    }
    
    turn = 0;
    bulletsFired = [];
    updateStatsUI();
}

function isCloseToSpawn(x, y) {
    // Keep 3x3 area around P1 Base (1, 11) and P1 Tank start (1, 8) clear
    // And rotationally symmetric areas clear
    const basesAndTanks = [
        {x: 1, y: 11}, // P1 Base
        {x: 1, y: 8},  // P1 Tank
        {x: 22, y: 12}, // P2 Base
        {x: 22, y: 15}  // P2 Tank
    ];

    for (let target of basesAndTanks) {
        if (Math.abs(x - target.x) <= 1 && Math.abs(y - target.y) <= 1) {
            return true;
        }
    }
    return false;
}

// Update Stats UI panels
function updateStatsUI() {
    for (let pId of [1, 2]) {
        document.getElementById(`p${pId}-hp`).innerText = `${players[pId].hp}/${players[pId].maxHp}`;
        document.getElementById(`p${pId}-fuel`).innerText = `${players[pId].fuel}/${players[pId].maxFuel}`;
        document.getElementById(`p${pId}-base-hp`).innerText = `${players[pId].baseHp}/${players[pId].maxBaseHp}`;
        document.getElementById(`p${pId}-dir`).innerText = players[pId].direction;
    }
}

// Render the 2D Game Board
function renderGame() {
    // Clear canvas
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw Grid Lines
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 1;
    for (let i = 0; i <= GRID_SIZE; i++) {
        const pos = i * CELL_PIXELS;
        ctx.beginPath();
        ctx.moveTo(pos, 0);
        ctx.lineTo(pos, canvas.height);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(0, pos);
        ctx.lineTo(canvas.width, pos);
        ctx.stroke();
    }

    // Draw Walls
    for (let y = 0; y < GRID_SIZE; y++) {
        for (let x = 0; x < GRID_SIZE; x++) {
            const cell = map[y][x];
            if (cell === CELL_INDESTRUCTIBLE) {
                // Dark steel wall
                ctx.fillStyle = '#4a4a62';
                ctx.fillRect(x * CELL_PIXELS + 2, y * CELL_PIXELS + 2, CELL_PIXELS - 4, CELL_PIXELS - 4);
                // Highlight border
                ctx.strokeStyle = '#6f6f93';
                ctx.lineWidth = 2;
                ctx.strokeRect(x * CELL_PIXELS + 2, y * CELL_PIXELS + 2, CELL_PIXELS - 4, CELL_PIXELS - 4);
            } else if (cell === CELL_DESTRUCTIBLE) {
                // Orange-red brick wall
                ctx.fillStyle = '#a64d32';
                ctx.fillRect(x * CELL_PIXELS + 2, y * CELL_PIXELS + 2, CELL_PIXELS - 4, CELL_PIXELS - 4);
                // Draw simple brick lines
                ctx.strokeStyle = '#732c18';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(x * CELL_PIXELS + 2, y * CELL_PIXELS + 10);
                ctx.lineTo(x * CELL_PIXELS + CELL_PIXELS - 2, y * CELL_PIXELS + 10);
                ctx.moveTo(x * CELL_PIXELS + 2, y * CELL_PIXELS + 18);
                ctx.lineTo(x * CELL_PIXELS + CELL_PIXELS - 2, y * CELL_PIXELS + 18);
                ctx.stroke();
            } else if (cell === CELL_BUSH) {
                // Green-tinted bush
                ctx.fillStyle = '#1e3e1e';
                ctx.fillRect(x * CELL_PIXELS + 2, y * CELL_PIXELS + 2, CELL_PIXELS - 4, CELL_PIXELS - 4);
                // Draw simple bush/grass icon
                ctx.fillStyle = '#2c5e2c';
                ctx.beginPath();
                ctx.arc(x * CELL_PIXELS + 8, y * CELL_PIXELS + 14, 4, 0, Math.PI * 2);
                ctx.arc(x * CELL_PIXELS + 12, y * CELL_PIXELS + 10, 5, 0, Math.PI * 2);
                ctx.arc(x * CELL_PIXELS + 16, y * CELL_PIXELS + 14, 4, 0, Math.PI * 2);
                ctx.fill();
            } else if (cell === CELL_FUEL) {
                // Distinct orange/yellow canister
                ctx.fillStyle = '#d35400'; // Darker orange base
                ctx.fillRect(x * CELL_PIXELS + 6, y * CELL_PIXELS + 6, 12, 12);
                ctx.fillStyle = '#f39c12'; // Yellow highlight
                ctx.fillRect(x * CELL_PIXELS + 8, y * CELL_PIXELS + 8, 8, 8);
                // Fuel icon (cross/plus)
                ctx.fillStyle = '#fff';
                ctx.fillRect(x * CELL_PIXELS + 11, y * CELL_PIXELS + 9, 2, 6);
                ctx.fillRect(x * CELL_PIXELS + 9, y * CELL_PIXELS + 11, 6, 2);
            }
        }
    }

    // Draw Bases
    // P1 Base (Yellow)
    drawBase(players[1].baseX, players[1].baseY, players[1].color);
    // P2 Base (Green)
    drawBase(players[2].baseX, players[2].baseY, players[2].color);

    // Draw Tanks
    // P1 Tank (Yellow)
    drawTank(players[1]);
    // P2 Tank (Green)
    drawTank(players[2]);

    // Draw Animated Traveling Bullet Projectiles & Impact Effects
    const now = performance.now();
    const delay = parseInt(speedSlider.value);
    // Bullet travels over 60% of turn time, then 25% gap of nothing before next turn
    const travelDuration = Math.max(80, delay * 0.6);
    const impactDuration = Math.max(40, delay * 0.15);

    bulletsFired.forEach(bullet => {
        const elapsed = now - (bullet.firedTime || now);
        if (elapsed > travelDuration + impactDuration) return;

        const startPx = bullet.startX * CELL_PIXELS + CELL_PIXELS / 2;
        const startPy = bullet.startY * CELL_PIXELS + CELL_PIXELS / 2;
        const endPx = bullet.endX * CELL_PIXELS + CELL_PIXELS / 2;
        const endPy = bullet.endY * CELL_PIXELS + CELL_PIXELS / 2;

        ctx.save();

        if (elapsed <= travelDuration) {
            // Phase 1: Projectile is flying from start to end
            const progress = Math.min(1.0, elapsed / travelDuration);
            const projX = startPx + (endPx - startPx) * progress;
            const projY = startPy + (endPy - startPy) * progress;

            // Outer glow
            ctx.shadowColor = bullet.color;
            ctx.shadowBlur = 14;
            ctx.fillStyle = bullet.color;
            ctx.beginPath();
            ctx.arc(projX, projY, 5, 0, Math.PI * 2);
            ctx.fill();

            // Bright white core
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(projX, projY, 2.5, 0, Math.PI * 2);
            ctx.fill();

            // Short fading trail (3 dots behind the projectile)
            const dirVec = DIR_VECTORS[bullet.dir] || { x: 1, y: 0 };
            for (let i = 1; i <= 3; i++) {
                const trailX = projX - dirVec.x * i * 6;
                const trailY = projY - dirVec.y * i * 6;
                // Don't draw trail behind the start position
                const dx = trailX - startPx;
                const dy = trailY - startPy;
                const behindStart = (dirVec.x !== 0 && Math.sign(dx) !== Math.sign(dirVec.x)) ||
                                    (dirVec.y !== 0 && Math.sign(dy) !== Math.sign(dirVec.y));
                if (behindStart) continue;

                ctx.globalAlpha = 0.6 - i * 0.18;
                ctx.fillStyle = bullet.color;
                ctx.beginPath();
                ctx.arc(trailX, trailY, 3 - i * 0.6, 0, Math.PI * 2);
                ctx.fill();
            }
        } else {
            // Phase 2: Impact flash at destination
            const impactElapsed = elapsed - travelDuration;
            const impactProgress = impactElapsed / impactDuration;
            const opacity = 1 - impactProgress;
            const radius = 4 + impactProgress * 10;

            ctx.globalAlpha = opacity;

            // Expanding ring
            ctx.strokeStyle = bullet.color;
            ctx.shadowColor = bullet.color;
            ctx.shadowBlur = 8;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(endPx, endPy, radius, 0, Math.PI * 2);
            ctx.stroke();

            // Center flash dot
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(endPx, endPy, 2 * (1 - impactProgress), 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();
    });
}

function drawBase(x, y, color) {
    const px = x * CELL_PIXELS;
    const py = y * CELL_PIXELS;
    
    // Draw star/diamond base shape
    ctx.fillStyle = color;
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(px + CELL_PIXELS/2, py + 2);
    ctx.lineTo(px + CELL_PIXELS - 2, py + CELL_PIXELS/2);
    ctx.lineTo(px + CELL_PIXELS/2, py + CELL_PIXELS - 2);
    ctx.lineTo(px + 2, py + CELL_PIXELS/2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Center core
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.arc(px + CELL_PIXELS/2, py + CELL_PIXELS/2, 4, 0, Math.PI*2);
    ctx.fill();
}

function drawTank(tank) {
    if (tank.hp <= 0) return; // Don't draw destroyed tanks
    if (tank.inBush) return; // Don't draw tanks hidden in bushes
    
    const px = tank.x * CELL_PIXELS;
    const py = tank.y * CELL_PIXELS;
    const center = CELL_PIXELS / 2;

    ctx.save();
    ctx.translate(px + center, py + center);

    // Rotate turret based on facing direction
    let angle = 0;
    if (tank.direction === 'DOWN') angle = Math.PI / 2;
    else if (tank.direction === 'LEFT') angle = Math.PI;
    else if (tank.direction === 'UP') angle = -Math.PI / 2;

    ctx.rotate(angle);

    // Tank Body (Rounded square/tracks)
    ctx.fillStyle = tank.color;
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    // Main base
    ctx.fillRect(-8, -8, 16, 16);
    ctx.strokeRect(-8, -8, 16, 16);

    // Tank Tracks (Left/Right from body rotation perspective, i.e., top/bottom in horizontal rotation)
    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(-10, -10, 20, 2);
    ctx.fillRect(-10, 8, 20, 2);

    // Turret center
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(0, 0, 4, 0, Math.PI * 2);
    ctx.fill();

    // Gun Barrel (pointing forward, i.e. to the right)
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(12, 0);
    ctx.stroke();

    ctx.restore();
}

// Get Python AI Move
async function getPythonBotMove(playerNum) {
    if (!pyodideInstance) {
        logToConsole(`[ERROR] Pyodide not loaded yet for P${playerNum}!`, 'damage-msg');
        return 'IDLE';
    }

    const player = players[playerNum];
    const opponent = players[playerNum === 1 ? 2 : 1];

    if (!player.code) {
        logToConsole(`[WARNING] No Python script uploaded for Player ${playerNum}. Defaulting to IDLE.`, 'damage-msg');
        return 'IDLE';
    }

    // Build state dictionary according to the specification
    // Map representation: flat list of lists or similar
    // Map has values: 0=empty, 1=indestructible, 2=destructible
    // Opponent history sorted recent first
    const cleanHistory = [...opponent.history].reverse();

    const state = {
        grid_size: GRID_SIZE,
        turn: turn,
        my_tank: {
            x: player.x,
            y: player.y,
            hp: player.hp,
            fuel: player.fuel,
            direction: player.direction
        },
        my_base: {
            x: player.baseX,
            y: player.baseY,
            hp: player.baseHp
        },
        opponent_tank: {
            x: opponent.inBush ? opponent.lastKnownX : opponent.x,
            y: opponent.inBush ? opponent.lastKnownY : opponent.y,
            hp: opponent.hp,
            fuel: opponent.fuel,
            direction: opponent.inBush ? 'UNKNOWN' : opponent.direction
        },
        opponent_base: {
            x: opponent.baseX,
            y: opponent.baseY,
            hp: opponent.baseHp
        },
        map: map,
        my_history: [...player.history].reverse(),
        opponent_history: cleanHistory
    };

    try {
        const ns = playerNum === 1 ? p1Namespace : p2Namespace;
        // Inject state as json to avoid direct pyodide object proxy leaks
        ns.set("state_json", JSON.stringify(state));
        
        const actionResult = await pyodideInstance.runPythonAsync(`
import json
import asyncio
state = json.loads(state_json)
result = get_move(state)
if asyncio.iscoroutine(result):
    action = await result
else:
    action = result
action
        `, { globals: ns });

        if (typeof actionResult === 'string') {
            const cleanAction = actionResult.toUpperCase().trim();
            const allowedActions = [
                'MOVE_UP', 'MOVE_DOWN', 'MOVE_LEFT', 'MOVE_RIGHT',
                'SHOOT', 'IDLE'
            ];
            if (allowedActions.includes(cleanAction)) {
                return cleanAction;
            } else {
                logToConsole(`[WARNING] P${playerNum} bot returned invalid action string "${cleanAction}". Defaulting to IDLE.`, 'damage-msg');
                return 'IDLE';
            }
        } else {
            logToConsole(`[WARNING] P${playerNum} bot did not return a string action. Defaulting to IDLE.`, 'damage-msg');
            return 'IDLE';
        }
    } catch (err) {
        logToConsole(`[PYTHON RUN ERROR P${playerNum} - Turn ${turn}]:\n${err.message}`, 'damage-msg');
        return 'IDLE';
    }
}

// Get Player Action (Manual or Bot)
async function getPlayerAction(playerNum) {
    const player = players[playerNum];
    if (player.type === 'manual') {
        // Return whatever action was registered by keys, or default to IDLE if none
        const act = player.currentAction || 'IDLE';
        player.currentAction = null; // Consume action
        return act;
    } else {
        return await getPythonBotMove(playerNum);
    }
}

let isProcessingTick = false;

// Single Game Tick (Execution of turns)
async function executeGameTick() {
    if (!isPlaying || isProcessingTick) return;

    // Check if both players are ready (if manual, we wait for input)
    if (players[1].type === 'manual' && players[1].currentAction === null) {
        // Wait for P1
        return;
    }
    if (players[2].type === 'manual' && players[2].currentAction === null) {
        // Wait for P2
        return;
    }

    isProcessingTick = true;
    turn++;
    bulletsFired = []; // Reset bullet lines
    
    const p1Bot = players[1].type === 'python';
    const p2Bot = players[2].type === 'python';
    
    if (p1Bot || p2Bot) {
        document.getElementById('thinking-indicator').style.display = 'block';
        await new Promise(r => setTimeout(r, 50)); // Allow UI to render
    }

    // Retrieve actions (await async bot moves)
    const a1 = await getPlayerAction(1);
    const a2 = await getPlayerAction(2);
    
    if (p1Bot || p2Bot) {
        document.getElementById('thinking-indicator').style.display = 'none';
    }

    logToConsole(`--- TURN ${turn} ---`, 'system-msg');

    // Store action in history
    players[1].history.push({ turn: turn, action: a1 });
    players[2].history.push({ turn: turn, action: a2 });

    // Validate Fuel Constraint
    let act1 = a1;
    let act2 = a2;

    if (players[1].fuel <= 0 && act1 !== 'IDLE') {
        logToConsole(`[P1] Out of fuel! Action "${act1}" forced to IDLE.`, 'damage-msg');
        act1 = 'IDLE';
    }
    if (players[2].fuel <= 0 && act2 !== 'IDLE') {
        logToConsole(`[P2] Out of fuel! Action "${act2}" forced to IDLE.`, 'damage-msg');
        act2 = 'IDLE';
    }

    // Deduct fuel (1 for move/shoot, 0 for idle)
    if (act1.startsWith('MOVE') || act1 === 'SHOOT') players[1].fuel = Math.max(0, players[1].fuel - 1);
    if (act2.startsWith('MOVE') || act2 === 'SHOOT') players[2].fuel = Math.max(0, players[2].fuel - 1);

    // Save starting positions for bullet checks
    const p1Start = { x: players[1].x, y: players[1].y, dir: players[1].direction };
    const p2Start = { x: players[2].x, y: players[2].y, dir: players[2].direction };

    logToConsole(`P1 Action: ${act1} | P2 Action: ${act2}`, 'action-msg');

    // 1. Calculate Bullet Paths (from start coordinates, before anyone moves)
    let p1BulletPath = [];
    let p2BulletPath = [];

    if (act1 === 'SHOOT') {
        p1BulletPath = calculateBulletPath(p1Start.x, p1Start.y, p1Start.dir);
        // Visual bullet line
        bulletsFired.push({
            startX: p1Start.x,
            startY: p1Start.y,
            endX: p1BulletPath.length > 0 ? p1BulletPath[p1BulletPath.length - 1].x : p1Start.x,
            endY: p1BulletPath.length > 0 ? p1BulletPath[p1BulletPath.length - 1].y : p1Start.y,
            dir: p1Start.dir,
            color: players[1].color,
            firedTime: performance.now()
        });
    }

    if (act2 === 'SHOOT') {
        p2BulletPath = calculateBulletPath(p2Start.x, p2Start.y, p2Start.dir);
        // Visual bullet line
        bulletsFired.push({
            startX: p2Start.x,
            startY: p2Start.y,
            endX: p2BulletPath.length > 0 ? p2BulletPath[p2BulletPath.length - 1].x : p2Start.x,
            endY: p2BulletPath.length > 0 ? p2BulletPath[p2BulletPath.length - 1].y : p2Start.y,
            dir: p2Start.dir,
            color: players[2].color,
            firedTime: performance.now()
        });
    }

    // 2. Resolve Movements
    let p1Proposed = calculateMove(players[1], act1);
    let p2Proposed = calculateMove(players[2], act2);

    // Apply facing direction changes immediately (even if movement gets blocked, the tank turns)
    if (act1.startsWith('MOVE_')) players[1].direction = act1.replace('MOVE_', '');
    if (act2.startsWith('MOVE_')) players[2].direction = act2.replace('MOVE_', '');

    // Validate boundaries and static walls/bases
    p1Proposed = validateProposedMove(1, p1Proposed);
    p2Proposed = validateProposedMove(2, p2Proposed);

    // Resolve mutual collisions
    // Rule: same-cell or swapping cancels movement
    let p1Moved = true;
    let p2Moved = true;

    if (p1Proposed.x === p2Proposed.x && p1Proposed.y === p2Proposed.y && (p1Start.x !== p2Start.x || p1Start.y !== p2Start.y)) {
        // Same cell collision
        logToConsole(`[COLLISION] Both tanks tried to move to (${p1Proposed.x}, ${p1Proposed.y})! Moves cancelled.`, 'damage-msg');
        p1Proposed = { x: p1Start.x, y: p1Start.y };
        p2Proposed = { x: p2Start.x, y: p2Start.y };
        p1Moved = false;
        p2Moved = false;
    } else if (p1Proposed.x === p2Start.x && p1Proposed.y === p2Start.y && p2Proposed.x === p1Start.x && p2Proposed.y === p1Start.y) {
        // Swap collision
        logToConsole(`[COLLISION] Tanks tried to pass through each other! Moves cancelled.`, 'damage-msg');
        p1Proposed = { x: p1Start.x, y: p1Start.y };
        p2Proposed = { x: p2Start.x, y: p2Start.y };
        p1Moved = false;
        p2Moved = false;
    }

    // Update positions
    players[1].x = p1Proposed.x;
    players[1].y = p1Proposed.y;
    players[2].x = p2Proposed.x;
    players[2].y = p2Proposed.y;

    // Process Bushes and Fuel Canisters for each player
    for (let pId of [1, 2]) {
        const player = players[pId];
        const currentCell = map[player.y][player.x];
        
        // Fuel Canister Pickup
        if (currentCell === CELL_FUEL) {
            player.fuel = player.fuel + 10;
            map[player.y][player.x] = CELL_EMPTY; // Consume canister
            logToConsole(`[ITEM] Player ${pId} picked up a Fuel Canister! (+10 fuel)`, 'system-msg');
        }
        
        // Bush Concealment
        if (currentCell === CELL_BUSH) {
            player.inBush = true;
        } else {
            player.inBush = false;
            // Update last known position when visible
            player.lastKnownX = player.x;
            player.lastKnownY = player.y;
        }
    }

    // 3. Apply Bullet Damage
    // A bullet path hits a tank if the tank's NEW position is inside the path.
    // If they moved away, they dodged it!
    
    // Check hits on Player 2 Tank
    if (p1BulletPath.some(cell => cell.x === players[2].x && cell.y === players[2].y)) {
        players[2].hp = Math.max(0, players[2].hp - 1);
        logToConsole(`[HIT] Player 1 shot Player 2 Tank! (remaining HP: ${players[2].hp})`, 'damage-msg');
    } else if (act1 === 'SHOOT' && p1BulletPath.some(cell => cell.x === p2Start.x && cell.y === p2Start.y) && p2Moved) {
        logToConsole(`[DODGE] Player 2 dodged Player 1's bullet!`, 'action-msg');
    }

    // Check hits on Player 1 Tank
    if (p2BulletPath.some(cell => cell.x === players[1].x && cell.y === players[1].y)) {
        players[1].hp = Math.max(0, players[1].hp - 1);
        logToConsole(`[HIT] Player 2 shot Player 1 Tank! (remaining HP: ${players[1].hp})`, 'damage-msg');
    } else if (act2 === 'SHOOT' && p2BulletPath.some(cell => cell.x === p1Start.x && cell.y === p1Start.y) && p1Moved) {
        logToConsole(`[DODGE] Player 1 dodged Player 2's bullet!`, 'action-msg');
    }

    // Check hits on Player 1 Base (P1 can shoot their own base, P2 can shoot it)
    let p1BaseHit = false;
    if (p1BulletPath.some(cell => cell.x === players[1].baseX && cell.y === players[1].baseY)) p1BaseHit = true;
    if (p2BulletPath.some(cell => cell.x === players[1].baseX && cell.y === players[1].baseY)) p1BaseHit = true;
    if (p1BaseHit) {
        players[1].baseHp = Math.max(0, players[1].baseHp - 1);
        logToConsole(`[BASE HIT] Player 1's Base was shot! (remaining HP: ${players[1].baseHp})`, 'damage-msg');
    }

    // Check hits on Player 2 Base
    let p2BaseHit = false;
    if (p1BulletPath.some(cell => cell.x === players[2].baseX && cell.y === players[2].baseY)) p2BaseHit = true;
    if (p2BulletPath.some(cell => cell.x === players[2].baseX && cell.y === players[2].baseY)) p2BaseHit = true;
    if (p2BaseHit) {
        players[2].baseHp = Math.max(0, players[2].baseHp - 1);
        logToConsole(`[BASE HIT] Player 2's Base was shot! (remaining HP: ${players[2].baseHp})`, 'damage-msg');
    }

    // 4. Destroy Hit Walls
    // Any destructible walls hit by bullet paths are destroyed
    for (let bullet of bulletsFired) {
        const lastCell = calculateBulletCollision(bullet.startX, bullet.startY, bullet.dir);
        // Let's resolve what the bullet actually hit
        if (lastCell && map[lastCell.y][lastCell.x] === CELL_DESTRUCTIBLE) {
            map[lastCell.y][lastCell.x] = CELL_EMPTY;
            logToConsole(`[DESTROY] Destructible wall at (${lastCell.x}, ${lastCell.y}) destroyed!`, 'action-msg');
        }
    }

    // Update UI and re-render board
    updateStatsUI();
    renderGame();

    // Check game termination
    checkMatchTermination();

    // If manual mode, clear status message
    if (isPlaying && !isRunningAutomatically()) {
        displayWaitingPrompt();
    }
    
    isProcessingTick = false;
}

// Calculate the full straight bullet path (array of cell coords)
function calculateBulletPath(startX, startY, dir) {
    const vec = DIR_VECTORS[dir];
    const path = [];
    let cx = startX + vec.x;
    let cy = startY + vec.y;

    while (cx >= 0 && cx < GRID_SIZE && cy >= 0 && cy < GRID_SIZE) {
        path.push({ x: cx, y: cy });
        
        // Stop bullet at indestructible wall, destructible wall, player base, or player tank
        const cell = map[cy][cx];
        if (cell === CELL_INDESTRUCTIBLE || cell === CELL_DESTRUCTIBLE) {
            break; // Hits solid wall
        }
        if ((cx === players[1].baseX && cy === players[1].baseY) || 
            (cx === players[2].baseX && cy === players[2].baseY)) {
            break; // Hits base
        }
        if ((cx === players[1].x && cy === players[1].y) || 
            (cx === players[2].x && cy === players[2].y)) {
            break; // Hits tank
        }
        cx += vec.x;
        cy += vec.y;
    }
    return path;
}

// Find the final coordinate where bullet collided
function calculateBulletCollision(startX, startY, dir) {
    const vec = DIR_VECTORS[dir];
    let cx = startX + vec.x;
    let cy = startY + vec.y;

    while (cx >= 0 && cx < GRID_SIZE && cy >= 0 && cy < GRID_SIZE) {
        const cell = map[cy][cx];
        if (cell === CELL_INDESTRUCTIBLE || cell === CELL_DESTRUCTIBLE) {
            return { x: cx, y: cy };
        }
        if ((cx === players[1].baseX && cy === players[1].baseY) || 
            (cx === players[2].baseX && cy === players[2].baseY)) {
            return { x: cx, y: cy };
        }
        if ((cx === players[1].x && cy === players[1].y) || 
            (cx === players[2].x && cy === players[2].y)) {
            return { x: cx, y: cy };
        }
        cx += vec.x;
        cy += vec.y;
    }
    return null;
}

// Calculate proposed new tank coordinate based on action
function calculateMove(tank, action) {
    const pos = { x: tank.x, y: tank.y };
    if (action.startsWith('MOVE_')) {
        const dir = action.replace('MOVE_', '');
        const vec = DIR_VECTORS[dir];
        pos.x += vec.x;
        pos.y += vec.y;
    }
    return pos;
}

// Validate proposed coordinates (bounds, walls, bases)
function validateProposedMove(playerNum, proposed) {
    const current = { x: players[playerNum].x, y: players[playerNum].y };

    // Bounds check
    if (proposed.x < 0 || proposed.x >= GRID_SIZE || proposed.y < 0 || proposed.y >= GRID_SIZE) {
        return current;
    }

    // Static Wall check
    const cell = map[proposed.y][proposed.x];
    if (cell === CELL_INDESTRUCTIBLE || cell === CELL_DESTRUCTIBLE) {
        return current;
    }

    // Base check (tanks cannot drive onto base cells)
    if ((proposed.x === players[1].baseX && proposed.y === players[1].baseY) ||
        (proposed.x === players[2].baseX && proposed.y === players[2].baseY)) {
        return current;
    }

    return proposed;
}

// Check termination conditions
function checkMatchTermination() {
    let p1Dead = players[1].hp <= 0 || players[1].baseHp <= 0;
    let p2Dead = players[2].hp <= 0 || players[2].baseHp <= 0;

    let p1NoFuel = players[1].fuel <= 0;
    let p2NoFuel = players[2].fuel <= 0;

    let matchOver = false;
    let resultMessage = '';

    if (p1Dead && p2Dead) {
        resultMessage = "MUTUAL DESTRUCTION! IT'S A DRAW!";
        matchOver = true;
    } else if (p1Dead) {
        resultMessage = "PLAYER 2 (GREEN) WINS!";
        matchOver = true;
    } else if (p2Dead) {
        resultMessage = "PLAYER 1 (YELLOW) WINS!";
        matchOver = true;
    } else if (p1NoFuel && p2NoFuel) {
        // Out of fuel game evaluation
        logToConsole("[SYSTEM] Both players out of fuel! Reaching tie-breaker evaluation.", 'system-msg');
        
        // Sum of Tank HP + Base HP
        const p1Score = players[1].hp + players[1].baseHp;
        const p2Score = players[2].hp + players[2].baseHp;

        if (p1Score > p2Score) {
            resultMessage = `PLAYER 1 WINS ON SCORE TIE-BREAKER! (${p1Score} vs ${p2Score})`;
        } else if (p2Score > p1Score) {
            resultMessage = `PLAYER 2 WINS ON SCORE TIE-BREAKER! (${p2Score} vs ${p1Score})`;
        } else {
            resultMessage = "ABSOLUTE TIE! BOTH HP & BASE HP EQUAL.";
        }
        matchOver = true;
    } else if (turn >= maxTurns) {
        resultMessage = `TIMEOUT DETECTED (Turn Limit ${maxTurns} reached)!`;
        matchOver = true;
    }

    if (matchOver) {
        isPlaying = false;
        clearInterval(gameInterval);
        logToConsole(`[MATCH OVER] ${resultMessage}`, 'win-msg');
        
        btnStart.disabled = false;
        btnPause.disabled = true;
        btnStart.innerText = "START MATCH";
    }
}

// Start Match loop
function startMatch() {
    if (isPlaying && !isPaused) return;

    if (!isPlaying) {
        // Fresh start
        isPlaying = true;
        isPaused = false;
        btnStart.innerText = "RUNNING...";
        btnStart.disabled = true;
        btnPause.disabled = false;
        btnPause.innerText = "PAUSE";
        logToConsole("[SYSTEM] Match started!", 'system-msg');
        
        if (isRunningAutomatically()) {
            startMatchLoop();
        } else {
            displayWaitingPrompt();
        }
    } else {
        // Resume from pause
        isPaused = false;
        btnPause.innerText = "PAUSE";
        logToConsole("[SYSTEM] Match resumed.", 'system-msg');
        
        if (isRunningAutomatically()) {
            startMatchLoop();
        } else {
            displayWaitingPrompt();
        }
    }
}

function startMatchLoop() {
    const delay = parseInt(speedSlider.value);
    gameInterval = setInterval(executeGameTick, delay);
}

function pauseMatchLoop() {
    clearInterval(gameInterval);
}

// Toggle Pause
function togglePause() {
    if (!isPlaying) return;

    if (isPaused) {
        isPaused = false;
        btnPause.innerText = "PAUSE";
        logToConsole("[SYSTEM] Resumed.", 'system-msg');
        if (isRunningAutomatically()) {
            startMatchLoop();
        }
    } else {
        isPaused = true;
        btnPause.innerText = "RESUME";
        logToConsole("[SYSTEM] Paused.", 'system-msg');
        if (isRunningAutomatically()) {
            pauseMatchLoop();
        }
    }
}

// Reset Game
function resetGame() {
    isPlaying = false;
    isPaused = false;
    clearInterval(gameInterval);
    
    btnStart.innerText = "START MATCH";
    btnStart.disabled = false;
    btnPause.innerText = "PAUSE";
    btnPause.disabled = true;
    
    generateSymmetricMap();
    renderGame();
    logToConsole("[SYSTEM] Match reset. New random map and stats generated.", 'system-msg');
}

// Display key prompts when waiting for human players
function displayWaitingPrompt() {
    const p1Wait = players[1].type === 'manual' && players[1].currentAction === null;
    const p2Wait = players[2].type === 'manual' && players[2].currentAction === null;

    let msg = '';
    if (p1Wait && p2Wait) {
        msg = "[MANUAL CONTROL] Waiting for Player 1 (WASD/Space/Q) and Player 2 (Arrows/Enter/Slash) keys...";
    } else if (p1Wait) {
        msg = "[MANUAL CONTROL] Waiting for Player 1 (WASD/Space/Q) keys...";
    } else if (p2Wait) {
        msg = "[MANUAL CONTROL] Waiting for Player 2 (Arrows/Enter/Slash) keys...";
    }

    if (msg) {
        logToConsole(msg, 'system-msg');
    }
}

// Keypress handler for manual control
function handleKeyDown(e) {
    if (!isPlaying || isPaused) return;

    let p1Acted = false;
    let p2Acted = false;

    // Player 1 Manual Actions
    if (players[1].type === 'manual' && players[1].currentAction === null) {
        const key = e.key.toLowerCase();
        if (key === 'w') { players[1].currentAction = 'MOVE_UP'; p1Acted = true; }
        else if (key === 's') { players[1].currentAction = 'MOVE_DOWN'; p1Acted = true; }
        else if (key === 'a') { players[1].currentAction = 'MOVE_LEFT'; p1Acted = true; }
        else if (key === 'd') { players[1].currentAction = 'MOVE_RIGHT'; p1Acted = true; }
        else if (key === ' ') { players[1].currentAction = 'SHOOT'; p1Acted = true; e.preventDefault(); } // Space key scrolling block
        else if (key === 'q') { players[1].currentAction = 'IDLE'; p1Acted = true; }
    }

    // Player 2 Manual Actions
    if (players[2].type === 'manual' && players[2].currentAction === null) {
        const key = e.key;
        if (key === 'ArrowUp') { players[2].currentAction = 'MOVE_UP'; p2Acted = true; e.preventDefault(); }
        else if (key === 'ArrowDown') { players[2].currentAction = 'MOVE_DOWN'; p2Acted = true; e.preventDefault(); }
        else if (key === 'ArrowLeft') { players[2].currentAction = 'MOVE_LEFT'; p2Acted = true; e.preventDefault(); }
        else if (key === 'ArrowRight') { players[2].currentAction = 'MOVE_RIGHT'; p2Acted = true; e.preventDefault(); }
        else if (key === 'Enter') { players[2].currentAction = 'SHOOT'; p2Acted = true; e.preventDefault(); }
        else if (key === '/') { players[2].currentAction = 'IDLE'; p2Acted = true; e.preventDefault(); }
    }

    // If a manual action occurred, trigger a check to see if we can execute the tick
    if (p1Acted || p2Acted) {
        executeGameTick();
    }
}
