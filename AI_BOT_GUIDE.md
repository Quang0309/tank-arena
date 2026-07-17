# 🤖 AI Agent Implementation Guide & Specifications

This guide is targeted at **AI developers** and **LLM code generation agents** creating Python tank controller algorithms for the 2D AI Tank Battle Arena.

---

## 📌 1. Python Bot Interface Protocol

Every Python bot script must define a top-level function named `get_move(state)`.

### Function Signature
```python
def get_move(state: dict) -> str:
    """
    Evaluates the current state of the game and returns an action string.
    
    :param state: Dictionary containing grid map, tank stats, base stats, and turn history.
    :return: One of the valid action strings:
             'MOVE_UP', 'MOVE_DOWN', 'MOVE_LEFT', 'MOVE_RIGHT', 'SHOOT', 'IDLE'
    """
    # Custom strategy algorithm logic here
    return "IDLE"
```

> ⚠️ **Important Constraints**:
> - The return value must be **case-insensitive**, but strictly one of the 6 valid action strings. Any invalid string or unhandled exception defaults the tank action to `'IDLE'` for that turn.
> - Code executes client-side inside Pyodide WASM. Standard Python 3.11 modules (`random`, `math`, `collections`, `heapq`) are available.
> - **Async bots supported**: `get_move` can be declared as `async def get_move(state)` to `await` network requests (e.g., calling an LLM API via `pyodide.http.pyfetch`). See `gemini_bot.py` for an example.

---

## 📡 2. Complete State Dictionary Schema

The `state` dictionary provided to `get_move(state)` contains all global knowledge about the match:

```python
{
    "grid_size": 24,           # Grid dimension (24x24)
    "turn": 12,                # Current turn integer (starts at 1)
    "my_tank": {
        "x": 3,                # Integer X position (0..23)
        "y": 8,                # Integer Y position (0..23)
        "hp": 4,               # Current tank Health Points
        "fuel": 42,            # Remaining fuel points
        "direction": "RIGHT"   # Current facing: "UP", "DOWN", "LEFT", "RIGHT"
    },
    "my_base": {
        "x": 1,                # Base X coordinate
        "y": 11,               # Base Y coordinate
        "hp": 7                # Current base Health Points
    },
    "opponent_tank": {
        "x": 18,               # Enemy tank X position
        "y": 15,               # Enemy tank Y position
        "hp": 5,               # Enemy tank HP
        "fuel": 38,            # Enemy tank fuel
        "direction": "LEFT"    # Enemy facing direction
    },
    "opponent_base": {
        "x": 22,               # Enemy base X coordinate
        "y": 12,               # Enemy base Y coordinate
        "hp": 9                # Enemy base HP
    },
    "map": [                   # 24x24 matrix: map[y][x]
        [0, 0, 1, 2, ...],
        ...
    ],
    "my_history": [            # Your own past actions, most recent turn first
        {"turn": 11, "action": "MOVE_RIGHT"},
        ...
    ],
    "opponent_history": [      # Sorted by most recent turn first
        {"turn": 11, "action": "MOVE_LEFT"},
        {"turn": 10, "action": "SHOOT"},
        ...
    ]
}
```

### Map Matrix Codes (`state["map"][y][x]`)
- `0`: **Empty Cell** (Passable by tanks, passable by bullets)
- `1`: **Indestructible Steel Wall** (Blocks tank movement, blocks bullets)
- `2`: **Destructible Brick Wall** (Blocks tank movement, destroyed when hit by a bullet)
- `3`: **Bush** (Passable by tanks and bullets. Conceals tank position)
- `4`: **Fuel Canister** (Passable by tanks and bullets. Grants +10 fuel when driven over)

### Bush Concealment Mechanics
If the opponent tank drives into a Bush (`3`), their exact position is hidden from your state data:
- `opponent_tank.x` and `opponent_tank.y` will freeze at their **last known position** before entering the bush.
- `opponent_tank.direction` will be set to `"UNKNOWN"`.
- You must deduce their location based on game logic, bullet trails, or blind-firing!

---

## ⚡ 3. Action Space & Game Mechanics Rules

| Action String | Movement Effect | Facing Direction Change | Fuel Cost |
| :--- | :--- | :--- | :--- |
| `"MOVE_UP"` | `y -= 1` | Facing set to `"UP"` | **1 Fuel** |
| `"MOVE_DOWN"` | `y += 1` | Facing set to `"DOWN"` | **1 Fuel** |
| `"MOVE_LEFT"` | `x -= 1` | Facing set to `"LEFT"` | **1 Fuel** |
| `"MOVE_RIGHT"` | `x += 1` | Facing set to `"RIGHT"` | **1 Fuel** |
| `"SHOOT"` | Remains in current cell | Unchanged | **1 Fuel** |
| `"IDLE"` | Remains in current cell | Unchanged | **0 Fuel** |

### Critical Execution Rules for AI Strategy

1. **Shooting Line of Sight**:
   - `SHOOT` fires a bullet instantly in your tank's **current `direction`**. You **cannot** pass a direction parameter to `SHOOT`.
   - To shoot in a different direction, you must first move in that direction (e.g. `MOVE_UP` turns facing to `"UP"`).
2. **Dodging & Simultaneous Resolution**:
   - Both players submit actions at the exact same moment.
   - If an opponent is aiming at your cell `(X, Y)` and shoots, but you execute a valid `MOVE_*` out of `(X, Y)` in the same turn, the incoming shot misses you!
3. **Collision Avoidance**:
   - Tanks cannot enter cells occupied by indestructible walls (`1`), destructible walls (`2`), your base, or the enemy base.
   - If both tanks move into the same cell simultaneously, both moves cancel and neither tank moves.
4. **Fuel Depletion**:
   - If your fuel reaches `0`, any movement or shooting action is automatically converted to `"IDLE"`.

---

## 💡 4. Starter Template & Strategy Algorithms

### Starter Template (`my_bot.py`)
```python
import random

def get_move(state):
    my_tank = state["my_tank"]
    my_x, my_y = my_tank["x"], my_tank["y"]
    my_dir = my_tank["direction"]
    my_fuel = my_tank["fuel"]
    
    opp_tank = state["opponent_tank"]
    opp_base = state["opponent_base"]
    
    # 1. Conservation check
    if my_fuel <= 0:
        return "IDLE"

    # 2. Line of Sight Attack Check
    target_x, target_y = opp_base["x"], opp_base["y"]
    if opp_base["hp"] <= 0:
        target_x, target_y = opp_tank["x"], opp_tank["y"]

    # Check if target is aligned in current facing direction
    if my_dir == "RIGHT" and my_y == target_y and target_x > my_x:
        return "SHOOT"
    elif my_dir == "LEFT" and my_y == target_y and target_x < my_x:
        return "SHOOT"
    elif my_dir == "DOWN" and my_x == target_x and target_y > my_y:
        return "SHOOT"
    elif my_dir == "UP" and my_x == target_x and target_y < my_y:
        return "SHOOT"

    # 3. Default to random exploration
    return random.choice(["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT"])
```

### Advanced BFS Pathfinding Starter Pattern
```python
from collections import deque

def find_shortest_path(start, target, grid_map, grid_size, obstacles):
    """Simple Breadth-First Search to find next step towards target."""
    queue = deque([(start[0], start[1], [])])
    visited = {start}

    while queue:
        cx, cy, path = queue.popleft()
        if (cx, cy) == target:
            return path[0] if path else None

        for action, dx, dy in [("MOVE_UP", 0, -1), ("MOVE_DOWN", 0, 1), ("MOVE_LEFT", -1, 0), ("MOVE_RIGHT", 1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and (nx, ny) not in visited:
                if grid_map[ny][nx] in [0, 3, 4] and (nx, ny) not in obstacles:
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [action]))
    return None
```
