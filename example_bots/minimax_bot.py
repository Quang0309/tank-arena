import random

def get_move(state):
    """
    Minimax Bot - Strategy:
    Uses a simple sequential Minimax search with Alpha-Beta pruning to depth 3.
    It simulates: Our Turn -> Opponent Turn -> Our Turn.
    Heuristic evaluates: HP difference, base HP difference, and distance to opponent base.
    """
    # 1. Parse current state
    my_tank = state["my_tank"]
    opp_tank = state["opponent_tank"]
    my_base = state["my_base"]
    opp_base = state["opponent_base"]
    grid_map = state["map"]
    grid_size = state["grid_size"]
    
    # Handle bush hiding (if opponent coordinates are hidden, assume they are at their base for the heuristic)
    opp_x = opp_tank["x"] if opp_tank["x"] is not None else opp_base["x"]
    opp_y = opp_tank["y"] if opp_tank["y"] is not None else opp_base["y"]
    opp_dir = opp_tank["direction"] if opp_tank["direction"] is not None else "UP"
    
    if my_tank["fuel"] <= 0:
        return "IDLE"

    # Static obstacles (we assume bases and indestructible walls can't be moved through)
    obstacles = set()
    obstacles.add((my_base["x"], my_base["y"]))
    obstacles.add((opp_base["x"], opp_base["y"]))
    for y in range(grid_size):
        for x in range(grid_size):
            if grid_map[y][x] == 1:
                obstacles.add((x, y))

    # All possible actions
    ACTIONS = ["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "SHOOT", "IDLE"]
    DIR_VECTORS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def manhattan(x1, y1, x2, y2):
        return abs(x1 - x2) + abs(y1 - y2)

    def evaluate(s_my_hp, s_my_base_hp, s_opp_hp, s_opp_base_hp, s_my_x, s_my_y, s_opp_x, s_opp_y):
        # High score is good for us
        score = 0
        # Winning is infinite
        if s_opp_hp <= 0 or s_opp_base_hp <= 0:
            return 99999
        if s_my_hp <= 0 or s_my_base_hp <= 0:
            return -99999
            
        # Material Advantage
        score += (s_my_hp - s_opp_hp) * 100
        score += (s_my_base_hp - s_opp_base_hp) * 50
        
        # Positioning: closer to their base is better
        dist_to_opp_base = manhattan(s_my_x, s_my_y, opp_base["x"], opp_base["y"])
        score -= dist_to_opp_base * 2
        
        # Threat: if they are too close to our base, penalty
        dist_to_my_base = manhattan(s_opp_x, s_opp_y, my_base["x"], my_base["y"])
        score += dist_to_my_base * 1.5

        return score

    def simulate_action(x, y, d, hp, bhp, action, target_hp, target_x, target_y, target_base_hp, t_base_x, t_base_y, my_base_x, my_base_y):
        # Simulates one entity's action. Returns new state vars.
        nx, ny, nd = x, y, d
        nhp = hp
        nbhp = bhp
        ntarget_hp = target_hp
        ntarget_base_hp = target_base_hp
        
        if action.startswith("MOVE_"):
            nd = action.replace("MOVE_", "")
            vx, vy = DIR_VECTORS[nd]
            tx, ty = x + vx, y + vy
            if 0 <= tx < grid_size and 0 <= ty < grid_size:
                if (tx, ty) not in obstacles and grid_map[ty][tx] != 2: # Treat destructible as wall for simple sim
                    nx, ny = tx, ty
        elif action == "SHOOT":
            # Check simple line of sight
            vx, vy = DIR_VECTORS[nd]
            cx, cy = x + vx, y + vy
            hit_something = False
            while 0 <= cx < grid_size and 0 <= cy < grid_size and not hit_something:
                if cx == target_x and cy == target_y:
                    ntarget_hp -= 1
                    hit_something = True
                elif cx == t_base_x and cy == t_base_y:
                    ntarget_base_hp -= 1
                    hit_something = True
                elif cx == my_base_x and cy == my_base_y:
                    nbhp -= 1
                    hit_something = True
                elif (cx, cy) in obstacles:
                    hit_something = True
                elif grid_map[cy][cx] == 2:
                    hit_something = True
                cx += vx
                cy += vy
        return nx, ny, nd, nhp, nbhp, ntarget_hp, ntarget_base_hp

    def minimax(depth, is_maximizing, alpha, beta, 
                m_x, m_y, m_d, m_hp, m_bhp,
                o_x, o_y, o_d, o_hp, o_bhp):
                    
        if depth == 0 or m_hp <= 0 or o_hp <= 0 or m_bhp <= 0 or o_bhp <= 0:
            return evaluate(m_hp, m_bhp, o_hp, o_bhp, m_x, m_y, o_x, o_y)

        if is_maximizing:
            max_eval = -float('inf')
            for action in ACTIONS:
                nx, ny, nd, nhp, nbhp, no_hp, no_bhp = simulate_action(
                    m_x, m_y, m_d, m_hp, m_bhp, action, 
                    o_hp, o_x, o_y, o_bhp, opp_base["x"], opp_base["y"],
                    my_base["x"], my_base["y"]
                )
                ev = minimax(depth - 1, False, alpha, beta, nx, ny, nd, nhp, nbhp, o_x, o_y, o_d, no_hp, no_bhp)
                max_eval = max(max_eval, ev)
                alpha = max(alpha, ev)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for action in ACTIONS:
                ox, oy, od, ohp, no_bhp, nm_hp, nm_bhp = simulate_action(
                    o_x, o_y, o_d, o_hp, o_bhp, action, 
                    m_hp, m_x, m_y, m_bhp, my_base["x"], my_base["y"],
                    opp_base["x"], opp_base["y"]
                )
                ev = minimax(depth - 1, True, alpha, beta, m_x, m_y, m_d, nm_hp, nm_bhp, ox, oy, od, ohp, no_bhp)
                min_eval = min(min_eval, ev)
                beta = min(beta, ev)
                if beta <= alpha:
                    break
            return min_eval

    # Root call
    best_score = -float('inf')
    best_actions = []
    
    # We randomize order to break ties unpredictably
    shuffled_actions = list(ACTIONS)
    random.shuffle(shuffled_actions)

    for action in shuffled_actions:
        nx, ny, nd, nhp, nbhp, no_hp, no_bhp = simulate_action(
            my_tank["x"], my_tank["y"], my_tank["direction"], my_tank["hp"], my_base["hp"], action,
            opp_tank["hp"], opp_x, opp_y, opp_base["hp"], opp_base["x"], opp_base["y"],
            my_base["x"], my_base["y"]
        )
        
        score = minimax(3, False, -float('inf'), float('inf'), 
                        nx, ny, nd, nhp, nbhp, 
                        opp_x, opp_y, opp_dir, no_hp, no_bhp)
                        
        if score > best_score:
            best_score = score
            best_actions = [action]
        elif score == best_score:
            best_actions.append(action)

    return random.choice(best_actions) if best_actions else "IDLE"
