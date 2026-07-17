"""
Smart Algorithmic Bot for Tank Battle 2D
=========================================
A purely algorithmic bot designed to beat human players.

Architecture:
1. BFS Pathfinding with destructible wall awareness
2. Line-of-sight analysis for shooting decisions
3. Threat detection and evasion
4. Priority-based decision engine
5. Fuel-aware planning

No LLM required — runs instantly every turn.
"""

import random
from collections import deque

# ============================================================
# CONSTANTS
# ============================================================
PASSABLE = {0, 3, 4}       # Empty, Bush, Fuel
DESTRUCTIBLE = 2           # Brick wall
INDESTRUCTIBLE = 1         # Steel wall

DIR_DELTAS = {
    "UP":    (0, -1),
    "DOWN":  (0,  1),
    "LEFT":  (-1, 0),
    "RIGHT": (1,  0),
}

MOVE_ACTIONS = {
    "UP":    "MOVE_UP",
    "DOWN":  "MOVE_DOWN",
    "LEFT":  "MOVE_LEFT",
    "RIGHT": "MOVE_RIGHT",
}

OPPOSITE_DIR = {
    "UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT",
}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def in_bounds(x, y, size):
    return 0 <= x < size and 0 <= y < size

def manhattan(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)

def get_cell(grid, x, y, size):
    if not in_bounds(x, y, size):
        return -1
    return grid[y][x]

# ============================================================
# LINE OF SIGHT
# ============================================================

def trace_line_of_sight(x, y, direction, state):
    """Trace what a bullet would hit from (x,y) facing direction.
    Returns: (hit_type, hit_x, hit_y, distance)
    hit_type: 'enemy_tank', 'enemy_base', 'my_base', 'brick', 'steel', 'nothing'
    """
    grid = state["map"]
    size = state["grid_size"]
    dx, dy = DIR_DELTAS[direction]
    
    opp = state["opponent_tank"]
    opp_base = state["opponent_base"]
    my_base = state["my_base"]
    
    cx, cy = x + dx, y + dy
    dist = 1
    
    while in_bounds(cx, cy, size):
        # Check enemy tank
        if opp["x"] is not None and cx == opp["x"] and cy == opp["y"]:
            return ("enemy_tank", cx, cy, dist)
        # Check enemy base
        if cx == opp_base["x"] and cy == opp_base["y"]:
            return ("enemy_base", cx, cy, dist)
        # Check own base
        if cx == my_base["x"] and cy == my_base["y"]:
            return ("my_base", cx, cy, dist)
        # Check walls
        cell = grid[cy][cx]
        if cell == INDESTRUCTIBLE:
            return ("steel", cx, cy, dist)
        if cell == DESTRUCTIBLE:
            return ("brick", cx, cy, dist)
        cx += dx
        cy += dy
        dist += 1
    
    return ("nothing", -1, -1, dist)

def is_enemy_aiming_at_me(state):
    """Check if the opponent is facing toward us and has a clear shot."""
    opp = state["opponent_tank"]
    my = state["my_tank"]
    
    if opp["x"] is None or opp["y"] is None or opp["direction"] is None:
        return False
    
    ox, oy = opp["x"], opp["y"]
    mx, my_y = my["x"], my["y"]
    odir = opp["direction"]
    
    # Check alignment
    dx, dy = DIR_DELTAS[odir]
    if dx != 0:  # Horizontal facing
        if oy != my_y:
            return False
        if dx > 0 and mx <= ox:
            return False
        if dx < 0 and mx >= ox:
            return False
    else:  # Vertical facing
        if ox != mx:
            return False
        if dy > 0 and my_y <= oy:
            return False
        if dy < 0 and my_y >= oy:
            return False
    
    # Trace from opponent to see if they can actually hit us
    hit_type, hx, hy, _ = trace_line_of_sight(ox, oy, odir, state)
    if hit_type == "enemy_tank":
        # From opponent's perspective, WE are the enemy tank
        # But our trace_line_of_sight uses our perspective. Let's do a manual check.
        pass
    
    # Manual trace from opponent
    grid = state["map"]
    size = state["grid_size"]
    cx, cy = ox + dx, oy + dy
    while in_bounds(cx, cy, size):
        if cx == mx and cy == my_y:
            return True
        cell = grid[cy][cx]
        if cell in (INDESTRUCTIBLE, DESTRUCTIBLE):
            return False
        # Check if own base blocks (from opponent's perspective, their base)
        ob = state["opponent_base"]
        mb = state["my_base"]
        if (cx == ob["x"] and cy == ob["y"]) or (cx == mb["x"] and cy == mb["y"]):
            return False
        cx += dx
        cy += dy
    return False

# ============================================================
# BFS PATHFINDING
# ============================================================

def bfs_path(start_x, start_y, goal_x, goal_y, state, allow_brick_destroy=False):
    """BFS shortest path from start to goal.
    If allow_brick_destroy=True, treat brick walls as passable (with extra cost marker).
    Returns list of (x, y) from start (exclusive) to goal (inclusive), or None.
    """
    grid = state["map"]
    size = state["grid_size"]
    my_base = state["my_base"]
    opp_base = state["opponent_base"]
    
    if start_x == goal_x and start_y == goal_y:
        return []
    
    visited = set()
    visited.add((start_x, start_y))
    queue = deque()
    queue.append((start_x, start_y, []))
    
    while queue:
        cx, cy, path = queue.popleft()
        
        for d_name, (dx, dy) in DIR_DELTAS.items():
            nx, ny = cx + dx, cy + dy
            
            if not in_bounds(nx, ny, size):
                continue
            if (nx, ny) in visited:
                continue
            
            cell = grid[ny][nx]
            
            # Goal reached — always allow stepping onto goal
            if nx == goal_x and ny == goal_y:
                return path + [(nx, ny)]
            
            # Can we move through this cell?
            is_passable = cell in PASSABLE
            is_brick = (cell == DESTRUCTIBLE) and allow_brick_destroy
            
            # Don't walk through bases (except the goal itself)
            is_base = (nx == my_base["x"] and ny == my_base["y"]) or \
                      (nx == opp_base["x"] and ny == opp_base["y"])
            
            if (is_passable or is_brick) and not is_base:
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(nx, ny)]))
    
    return None  # No path found

def bfs_path_weighted(start_x, start_y, goal_x, goal_y, state):
    """Find path to goal, preferring paths without brick walls.
    First try without destroying bricks, then with."""
    path = bfs_path(start_x, start_y, goal_x, goal_y, state, allow_brick_destroy=False)
    if path is not None:
        return path, False
    path = bfs_path(start_x, start_y, goal_x, goal_y, state, allow_brick_destroy=True)
    if path is not None:
        return path, True
    return None, False

def direction_to_target(my_x, my_y, target_x, target_y):
    """Get the direction from (my_x, my_y) to an adjacent (target_x, target_y)."""
    dx = target_x - my_x
    dy = target_y - my_y
    for d_name, (ddx, ddy) in DIR_DELTAS.items():
        if ddx == dx and ddy == dy:
            return d_name
    return None

# ============================================================
# DODGE LOGIC
# ============================================================

def get_dodge_moves(state):
    """If enemy is aiming at us, return list of safe perpendicular moves."""
    my = state["my_tank"]
    opp = state["opponent_tank"]
    grid = state["map"]
    size = state["grid_size"]
    
    if opp["direction"] is None:
        return []
    
    odir = opp["direction"]
    dodge_dirs = []
    
    # Perpendicular directions
    if odir in ("UP", "DOWN"):
        dodge_dirs = ["LEFT", "RIGHT"]
    else:
        dodge_dirs = ["UP", "DOWN"]
    
    valid_dodges = []
    for d in dodge_dirs:
        dx, dy = DIR_DELTAS[d]
        nx, ny = my["x"] + dx, my["y"] + dy
        if in_bounds(nx, ny, size):
            cell = grid[ny][nx]
            my_base = state["my_base"]
            opp_base = state["opponent_base"]
            is_base = (nx == my_base["x"] and ny == my_base["y"]) or \
                      (nx == opp_base["x"] and ny == opp_base["y"])
            if cell in PASSABLE and not is_base:
                valid_dodges.append(MOVE_ACTIONS[d])
    
    return valid_dodges

# ============================================================
# FUEL AWARENESS
# ============================================================

def find_nearest_fuel(state):
    """Find the nearest fuel canister using BFS."""
    my = state["my_tank"]
    grid = state["map"]
    size = state["grid_size"]
    
    best_path = None
    best_dist = float('inf')
    
    for y in range(size):
        for x in range(size):
            if grid[y][x] == 4:  # Fuel canister
                dist = manhattan(my["x"], my["y"], x, y)
                if dist < best_dist:
                    path = bfs_path(my["x"], my["y"], x, y, state, allow_brick_destroy=False)
                    if path is not None and len(path) < best_dist:
                        best_path = path
                        best_dist = len(path)
    
    return best_path

# ============================================================
# MAIN DECISION ENGINE
# ============================================================

def get_move(state):
    my = state["my_tank"]
    opp = state["opponent_tank"]
    my_base = state["my_base"]
    opp_base = state["opponent_base"]
    grid = state["map"]
    size = state["grid_size"]
    
    mx, my_y = my["x"], my["y"]
    facing = my["direction"]
    fuel = my["fuel"]
    
    if fuel <= 0:
        return "IDLE"
    
    # -------------------------------------------------------
    # PRIORITY 1: SHOOT if we have a clear shot at enemy
    # -------------------------------------------------------
    hit_type, hx, hy, dist = trace_line_of_sight(mx, my_y, facing, state)
    
    if hit_type == "enemy_tank":
        return "SHOOT"
    
    if hit_type == "enemy_base":
        return "SHOOT"
    
    # Check all 4 directions for a shot opportunity (requires turning first)
    best_shot = None
    best_shot_priority = 0  # 2=enemy_base, 3=enemy_tank
    
    for d_name, (dx, dy) in DIR_DELTAS.items():
        if d_name == facing:
            continue  # Already checked above
        ht, shx, shy, sdist = trace_line_of_sight(mx, my_y, d_name, state)
        if ht == "enemy_tank" and best_shot_priority < 3:
            best_shot = d_name
            best_shot_priority = 3
        elif ht == "enemy_base" and best_shot_priority < 2:
            best_shot = d_name
            best_shot_priority = 2
    
    # -------------------------------------------------------
    # PRIORITY 2: DODGE if enemy is aiming at us
    # -------------------------------------------------------
    enemy_aiming = is_enemy_aiming_at_me(state)
    
    if enemy_aiming:
        dodges = get_dodge_moves(state)
        if dodges:
            # If we can dodge AND get a shot next turn, pick that dodge direction
            if best_shot:
                dodge_toward_shot = MOVE_ACTIONS.get(best_shot)
                if dodge_toward_shot in dodges:
                    return dodge_toward_shot
            return random.choice(dodges)
    
    # -------------------------------------------------------
    # PRIORITY 3: Turn to shoot if we see enemy in another direction
    # (but only if enemy won't shoot us this turn)
    # -------------------------------------------------------
    if best_shot and not enemy_aiming:
        # Turn to face the target (the turn itself changes direction)
        return MOVE_ACTIONS[best_shot]
    
    # -------------------------------------------------------
    # PRIORITY 4: Shoot brick walls along our path
    # -------------------------------------------------------
    # Check if we're facing a brick wall that's on our path to enemy base
    if hit_type == "brick":
        # Is this brick on our planned path?
        path_to_base, needs_destroy = bfs_path_weighted(mx, my_y, opp_base["x"], opp_base["y"], state)
        if path_to_base and needs_destroy:
            # Check if the brick wall we're facing is on or near the path
            if (hx, hy) in [(p[0], p[1]) for p in path_to_base]:
                return "SHOOT"
    
    # -------------------------------------------------------
    # PRIORITY 5: Navigate toward enemy base
    # -------------------------------------------------------
    path_to_base, needs_destroy = bfs_path_weighted(mx, my_y, opp_base["x"], opp_base["y"], state)
    
    if path_to_base and len(path_to_base) > 0:
        next_x, next_y = path_to_base[0]
        next_cell = grid[next_y][next_x]
        
        # If next step is a brick wall, face it and shoot
        if next_cell == DESTRUCTIBLE:
            needed_dir = direction_to_target(mx, my_y, next_x, next_y)
            if needed_dir:
                if facing == needed_dir:
                    return "SHOOT"
                else:
                    return MOVE_ACTIONS[needed_dir]
        
        # Normal movement
        needed_dir = direction_to_target(mx, my_y, next_x, next_y)
        if needed_dir:
            return MOVE_ACTIONS[needed_dir]
    
    # -------------------------------------------------------
    # PRIORITY 6: Hunt the enemy tank if no path to base
    # -------------------------------------------------------
    if opp["x"] is not None and opp["y"] is not None:
        path_to_tank = bfs_path(mx, my_y, opp["x"], opp["y"], state, allow_brick_destroy=True)
        if path_to_tank and len(path_to_tank) > 0:
            next_x, next_y = path_to_tank[0]
            next_cell = grid[next_y][next_x]
            
            if next_cell == DESTRUCTIBLE:
                needed_dir = direction_to_target(mx, my_y, next_x, next_y)
                if needed_dir:
                    if facing == needed_dir:
                        return "SHOOT"
                    else:
                        return MOVE_ACTIONS[needed_dir]
            
            needed_dir = direction_to_target(mx, my_y, next_x, next_y)
            if needed_dir:
                return MOVE_ACTIONS[needed_dir]
    
    # -------------------------------------------------------
    # PRIORITY 7: Low fuel — seek fuel canisters
    # -------------------------------------------------------
    if fuel < 15:
        fuel_path = find_nearest_fuel(state)
        if fuel_path and len(fuel_path) > 0:
            next_x, next_y = fuel_path[0]
            needed_dir = direction_to_target(mx, my_y, next_x, next_y)
            if needed_dir:
                return MOVE_ACTIONS[needed_dir]
    
    # -------------------------------------------------------
    # FALLBACK: Move toward enemy base by manhattan distance
    # -------------------------------------------------------
    best_move = "IDLE"
    best_dist = manhattan(mx, my_y, opp_base["x"], opp_base["y"])
    
    for d_name, (dx, dy) in DIR_DELTAS.items():
        nx, ny = mx + dx, my_y + dy
        if in_bounds(nx, ny, size):
            cell = grid[ny][nx]
            is_base = (nx == my_base["x"] and ny == my_base["y"]) or \
                      (nx == opp_base["x"] and ny == opp_base["y"])
            if cell in PASSABLE and not is_base:
                d = manhattan(nx, ny, opp_base["x"], opp_base["y"])
                if d < best_dist:
                    best_dist = d
                    best_move = MOVE_ACTIONS[d_name]
    
    return best_move
