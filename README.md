# 🎮 Retro 2D AI Tank Battle Arena

A strategy-focused, simultaneous turn-based 2D tank battle arena web application. The core feature of this game is that players can play manually or write/upload custom **Python algorithms (`.py` files)** that run client-side directly in the browser via **Pyodide (WebAssembly)** with zero server-side setup required.

![Arcade Tank Battle](https://img.shields.io/badge/Engine-Pyodide%20WASM-orange)
![License](https://img.shields.io/badge/License-MIT-blue)
![Platform](https://img.shields.io/badge/Platform-Web%20Browser-brightgreen)

---

## 🌟 Key Features

- **Zero-Install Python Execution**: Upload Python scripts (`.py`) directly in the UI. Code is executed safely and instantly inside the browser using Pyodide (WASM).
- **Simultaneous Turn System**: Both tanks commit an action concurrently each turn. Strategy, prediction, and dodging are essential!
- **Dual Victory Conditions**: Win by either destroying the enemy tank or destroying the enemy command base.
- **Fair Symmetrical Maps**: Grid obstacles (indestructible steel blocks & destructible brick walls) and starting bases are generated with 180° rotational symmetry.
- **Fuel & Resource Management**: Every move and shot consumes 1 fuel. Idling saves fuel. If fuel runs out, tanks cannot act!
- **Arcade Visual Aesthetics**: Retro pixel font, clean visual indicators, fading projectile trail effects, and impact spark explosions.

---

## 🚀 Quick Start (Run Locally)

Since the entire application is client-side, you can host it using any simple static file server.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/AI-TankGame.git
   cd AI-TankGame
   ```

2. **Start a local HTTP server**:
   ```bash
   python3 -m http.server 8080
   ```

3. **Open in browser**:
   Navigate to `http://localhost:8080` in Chrome, Firefox, Safari, or Edge.

---

## 🕹️ Game Rules & Mechanics

### 1. Grid & Coordinates
- The arena is a **24x24 grid**.
- Coordinates run from `(0, 0)` at top-left to `(23, 23)` at bottom-right.

### 2. Stats & Randomization
At the start of every match, the game randomizes the following parameters to ensure strategy must adapt dynamically:
- **Tank HP**: Randomized between 3 and 6.
- **Base HP**: Randomized between 5 and 10.
- **Starting Fuel**: Randomized between 40 and 60.

### 3. Victory Conditions
A player wins when:
1. The **enemy tank's HP** reaches `0`.
2. The **enemy command base's HP** reaches `0`.
3. *(Tie-Breaker)* If both players run out of fuel, the player with higher combined `(Tank HP + Base HP)` wins.

### 4. Facing Direction & Action Space
Tanks face one of four directions (`UP`, `DOWN`, `LEFT`, `RIGHT`).

Each turn, a tank can choose **one** of the following actions:
- `MOVE_UP`: Facing turns `UP`, tank moves 1 cell up. (Costs 1 fuel)
- `MOVE_DOWN`: Facing turns `DOWN`, tank moves 1 cell down. (Costs 1 fuel)
- `MOVE_LEFT`: Facing turns `LEFT`, tank moves 1 cell left. (Costs 1 fuel)
- `MOVE_RIGHT`: Facing turns `RIGHT`, tank moves 1 cell right. (Costs 1 fuel)
- `SHOOT`: Fires a bullet in current facing direction. Tank does not move. (Costs 1 fuel)
- `IDLE`: Do nothing. Tank maintains position and direction. (Costs 0 fuel)

### 5. Terrain Features
- **Empty Cells**: Passable by tanks and bullets.
- **Indestructible Steel Walls**: Block tanks and bullets.
- **Destructible Brick Walls**: Block tanks, but are destroyed when hit by a bullet.
- **Bushes**: Passable by tanks and bullets. If a tank drives into a bush, it becomes completely invisible to the opponent (including AI bots, which will only receive the tank's last known coordinates before entering the bush).
- **Fuel Canisters**: Passable by tanks and bullets. Driving over a fuel canister consumes it and grants +10 fuel.

### 6. Simultaneous Turn Physics & Dodging
- **Facing Update**: Facing direction updates immediately when moving.
- **Bullet Speed & Dodging**: Shooting and moving occur simultaneously.
  - If Tank A shoots at cell `(X, Y)` where Tank B was standing, but Tank B moves to `(X+1, Y)` during that exact turn, **Tank B successfully dodges the bullet**!
  - If Tank B moves *into* the path of an oncoming bullet, **Tank B takes damage**.
- **Collisions**:
  - If both tanks attempt to move into the exact same cell in the same turn, both moves are canceled and tanks stay in place.
  - Tanks cannot drive onto walls or command bases.

---

## 🎮 Manual Controls

You can set Player 1 or Player 2 to **Manual** mode to play using your keyboard:

| Control | Player 1 (Yellow) | Player 2 (Green) |
| :--- | :--- | :--- |
| **Move Up** | `W` | `Up Arrow` |
| **Move Down** | `S` | `Down Arrow` |
| **Move Left** | `A` | `Left Arrow` |
| **Move Right** | `D` | `Right Arrow` |
| **Shoot** | `Spacebar` | `Enter` |
| **Idle / Pass** | `Q` | `/` |

---

## 🤖 How to Play with Custom Python Bots

1. Set the **Control Type** dropdown for Player 1 or Player 2 to **Python Script**.
2. Click **UPLOAD P1/P2 .PY BOT** and select your Python file.
3. Example bots are provided in the [`example_bots/`](file:///Users/quangnguyen/Documents/Master_Courses/Self_Study/AI-TankGame/example_bots) folder:
   - `idle_bot.py`: Baseline bot that conserves fuel.
   - `random_bot.py`: Random movement and shooting algorithm.
   - `seeker_bot.py`: Greedy pathfinder that navigates obstacles, targets bases, and shoots destructible walls.
4. Click **START MATCH** to watch your bots compete!

---

## 📄 Documentation for AI Agents & Developers

For complete state schemas, AI bot interface specs, and pathfinding guidelines, refer to [**AI_BOT_GUIDE.md**](AI_BOT_GUIDE.md).
