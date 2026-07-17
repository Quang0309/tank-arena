import random

def get_move(state):
    """
    Seeker Bot - Strategy:
    1. Identify a target (opponent base if alive, otherwise opponent tank).
    2. Check if the target is in the line of fire (same row or col and facing it). If so, SHOOT.
    3. If there is a destructible wall in front of us blocking our path, SHOOT to destroy it.
    4. Otherwise, move closer to the target using a simple greedy step.
    """
    my_tank = state["my_tank"]
    my_x, my_y = my_tank["x"], my_tank["y"]
    my_dir = my_tank["direction"]
    my_fuel = my_tank["fuel"]
    
    opp_base = state["opponent_base"]
    opp_tank = state["opponent_tank"]
    
    # Target prioritisation: base first, then tank
    target_x, target_y = opp_base["x"], opp_base["y"]
    if opp_base["hp"] <= 0:
        target_x, target_y = opp_tank["x"], opp_tank["y"]
        
    grid_map = state["map"]
    grid_size = state["grid_size"]

    # 1. Line of Sight Check (Check if target is aligned and facing it)
    is_aligned = False
    correct_dir = None
    
    if my_x == target_x:
        is_aligned = True
        correct_dir = "DOWN" if target_y > my_y else "UP"
    elif my_y == target_y:
        is_aligned = True
        correct_dir = "RIGHT" if target_x > my_x else "LEFT"
        
    if is_aligned and my_dir == correct_dir:
        # Check if there is an indestructible wall in the way before shooting
        has_indestructible_block = False
        step = 1 if (target_x > my_x or target_y > my_y) else -1
        
        if my_x == target_x:
            for y_check in range(my_y + step, target_y, step):
                if grid_map[y_check][my_x] == 1: # Indestructible
                    has_indestructible_block = True
                    break
        else:
            for x_check in range(my_x + step, target_x, step):
                if grid_map[my_y][x_check] == 1:
                    has_indestructible_block = True
                    break
                    
        if not has_indestructible_block:
            return "SHOOT"

    # 2. Check for destructible wall directly in front of us
    dir_vectors = {
        "UP": (0, -1),
        "DOWN": (0, 1),
        "LEFT": (-1, 0),
        "RIGHT": (1, 0)
    }
    
    front_dx, front_dy = dir_vectors[my_dir]
    front_x, front_y = my_x + front_dx, my_y + front_dy
    
    if 0 <= front_x < grid_size and 0 <= front_y < grid_size:
        if grid_map[front_y][front_x] == 2: # Destructible wall
            return "SHOOT"

    # 3. Pathfinding / Movement: greedy Manhattan move towards target
    dx = target_x - my_x
    dy = target_y - my_y
    
    possible_moves = []
    if dx > 0:
        possible_moves.append(("MOVE_RIGHT", my_x + 1, my_y))
    elif dx < 0:
        possible_moves.append(("MOVE_LEFT", my_x - 1, my_y))
        
    if dy > 0:
        possible_moves.append(("MOVE_DOWN", my_x, my_y + 1))
    elif dy < 0:
        possible_moves.append(("MOVE_UP", my_x, my_y - 1))
        
    # Shuffle options to avoid getting stuck in loops
    random.shuffle(possible_moves)
    
    # Try moves that are unblocked
    for move_action, nx, ny in possible_moves:
        if 0 <= nx < grid_size and 0 <= ny < grid_size:
            # Empty cell, bush, or fuel and not walking onto opponent base
            if grid_map[ny][nx] in [0, 3, 4] and not (nx == state["my_base"]["x"] and ny == state["my_base"]["y"]):
                return move_action
                
    # If standard directions are blocked, try any open direction to navigate around obstacles
    all_directions = list(dir_vectors.items())
    random.shuffle(all_directions)
    for d_name, (vx, vy) in all_directions:
        nx, ny = my_x + vx, my_y + vy
        if 0 <= nx < grid_size and 0 <= ny < grid_size:
            if grid_map[ny][nx] in [0, 3, 4] and not (nx == state["my_base"]["x"] and ny == state["my_base"]["y"]):
                return f"MOVE_{d_name}"
                
    # Default to IDLE if completely stuck
    return "IDLE"
