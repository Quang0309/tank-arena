import random
import heapq

def get_move(state):
    """
    Terminator Bot - Strategy:
    1. Base Assaulter: Pathfind to enemy base.
    2. Predictive Dodging: If the opponent shot last turn, and we are in LOS, dodge.
    3. Weighted A*: Prioritize stealth (bushes) over empty cells.
    """
    my_tank = state["my_tank"]
    my_x, my_y = my_tank["x"], my_tank["y"]
    my_dir = my_tank["direction"]
    my_fuel = my_tank["fuel"]
    
    opp_tank = state["opponent_tank"]
    opp_base = state["opponent_base"]
    
    grid_map = state["map"]
    grid_size = state["grid_size"]
    opp_history = state["opponent_history"]

    if my_fuel <= 0:
        return "IDLE"

    # --- 1. Line of Sight (LOS) Calculation ---
    def in_los(tx, ty, t_dir, target_x, target_y):
        if tx == target_x:
            step = 1 if target_y > ty else -1
            if (t_dir == "DOWN" and step == 1) or (t_dir == "UP" and step == -1):
                for y_check in range(ty + step, target_y, step):
                    if grid_map[y_check][tx] == 1: # Indestructible wall blocks LOS
                        return False
                return True
        elif ty == target_y:
            step = 1 if target_x > tx else -1
            if (t_dir == "RIGHT" and step == 1) or (t_dir == "LEFT" and step == -1):
                for x_check in range(tx + step, target_x, step):
                    if grid_map[ty][x_check] == 1:
                        return False
                return True
        return False

    # --- 2. Predictive Dodging ---
    # Did opponent shoot last turn?
    opp_shot_last_turn = False
    if len(opp_history) > 0 and opp_history[0]["action"] == "SHOOT":
        opp_shot_last_turn = True

    # Are we in opponent's LOS?
    in_opp_los = in_los(opp_tank["x"], opp_tank["y"], opp_tank["direction"], my_x, my_y)

    if opp_shot_last_turn and in_opp_los and my_fuel > 2:
        # Dodge perpendicular
        dodge_moves = []
        if opp_tank["x"] == my_x: # Opponent is vertically aligned
            dodge_moves = [("MOVE_LEFT", -1, 0), ("MOVE_RIGHT", 1, 0)]
        else: # Opponent is horizontally aligned
            dodge_moves = [("MOVE_UP", 0, -1), ("MOVE_DOWN", 0, 1)]
        
        random.shuffle(dodge_moves)
        for action, dx, dy in dodge_moves:
            nx, ny = my_x + dx, my_y + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                if grid_map[ny][nx] in [0, 3, 4] and not (nx == state["my_base"]["x"] and ny == state["my_base"]["y"]):
                    return action

    # --- 3. Attack Check ---
    target_x, target_y = opp_base["x"], opp_base["y"]
    if opp_base["hp"] <= 0:
        target_x, target_y = opp_tank["x"], opp_tank["y"]

    if in_los(my_x, my_y, my_dir, target_x, target_y):
        return "SHOOT"

    # --- 4. Shoot Destructible Wall in front ---
    dir_vectors = {
        "UP": (0, -1), "DOWN": (0, 1),
        "LEFT": (-1, 0), "RIGHT": (1, 0)
    }
    front_dx, front_dy = dir_vectors[my_dir]
    front_x, front_y = my_x + front_dx, my_y + front_dy
    if 0 <= front_x < grid_size and 0 <= front_y < grid_size:
        if grid_map[front_y][front_x] == 2:
            return "SHOOT"

    # --- 5. Weighted A* Pathfinding ---
    def get_terrain_cost(cell_value):
        if cell_value == 3: # Bush
            return 1
        elif cell_value in [0, 4]: # Empty / Fuel
            return 2
        elif cell_value == 2: # Destructible wall
            return 5
        return float('inf') # Indestructible / other

    def heuristic(x1, y1, x2, y2):
        return abs(x1 - x2) + abs(y1 - y2)

    open_set = []
    heapq.heappush(open_set, (0, 0, my_x, my_y, None))
    came_from = {}
    g_score = {(my_x, my_y): 0}
    
    obstacles = {(state["my_base"]["x"], state["my_base"]["y"]), (opp_base["x"], opp_base["y"])}
    if opp_tank["hp"] > 0:
        obstacles.add((opp_tank["x"], opp_tank["y"]))

    found_path = False
    while open_set:
        _, current_g, cx, cy, first_action = heapq.heappop(open_set)

        if cx == target_x and cy == target_y:
            found_path = True
            break
            
        # Stop near target to shoot
        if heuristic(cx, cy, target_x, target_y) == 1:
            found_path = True
            break

        for d_name, (dx, dy) in dir_vectors.items():
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and (nx, ny) not in obstacles:
                cell = grid_map[ny][nx]
                cost = get_terrain_cost(cell)
                if cost == float('inf'):
                    continue
                
                tentative_g = current_g + cost
                if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                    g_score[(nx, ny)] = tentative_g
                    f_score = tentative_g + heuristic(nx, ny, target_x, target_y) * 2 # prioritize heuristic a bit
                    action = first_action if first_action else f"MOVE_{d_name}"
                    heapq.heappush(open_set, (f_score, tentative_g, nx, ny, action))
                    
    # The popped item from loop gives us the best first action if we found path
    if found_path and first_action:
        # Check if the next step is actually moving into a destructible wall, we can't move into it!
        # A* doesn't simulate turns. If our chosen move action goes into a cell with a destructible wall,
        # we will just turn to face it this turn. The "Shoot Destructible Wall in front" block will fire NEXT turn.
        # However, if we are ALREADY facing it, we would have shot it in block 4!
        # So we can safely return the MOVE command. If it hits a destructible wall, the tank will just turn.
        return first_action

    # 6. Fallback exploration
    possible_moves = []
    for d_name, (vx, vy) in dir_vectors.items():
        nx, ny = my_x + vx, my_y + vy
        if 0 <= nx < grid_size and 0 <= ny < grid_size:
            if grid_map[ny][nx] in [0, 3, 4] and (nx, ny) not in obstacles:
                possible_moves.append(f"MOVE_{d_name}")
                
    if possible_moves:
        return random.choice(possible_moves)

    return "IDLE"
