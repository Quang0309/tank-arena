import random
import time
import math

class Node:
    def __init__(self, state, parent=None, action=None):
        self.state = state  # State tuple: (my_x, my_y, my_d, my_hp, my_bhp, opp_x, opp_y, opp_d, opp_hp, opp_bhp)
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_actions = ["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "SHOOT", "IDLE"]

    def ucb1(self, exploration_weight=1.414):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + exploration_weight * math.sqrt(math.log(self.parent.visits) / self.visits)

def get_move(state):
    """
    Monte Carlo Tree Search (MCTS) Bot
    Runs random playouts to determine the best move.
    Bounded by a strict time limit to avoid freezing the browser.
    """
    start_time = time.time()
    TIME_LIMIT = 0.4  # Max 400ms thinking time

    my_tank = state["my_tank"]
    opp_tank = state["opponent_tank"]
    my_base = state["my_base"]
    opp_base = state["opponent_base"]
    grid_map = state["map"]
    grid_size = state["grid_size"]
    
    # Handle bush hiding (if opponent coordinates are hidden, assume they are at their base)
    opp_x = opp_tank["x"] if opp_tank["x"] is not None else opp_base["x"]
    opp_y = opp_tank["y"] if opp_tank["y"] is not None else opp_base["y"]
    opp_dir = opp_tank["direction"] if opp_tank["direction"] is not None else "UP"
    
    if my_tank["fuel"] <= 0:
        return "IDLE"

    obstacles = set()
    obstacles.add((my_base["x"], my_base["y"]))
    obstacles.add((opp_base["x"], opp_base["y"]))
    for y in range(grid_size):
        for x in range(grid_size):
            if grid_map[y][x] == 1:
                obstacles.add((x, y))

    DIR_VECTORS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def simulate_action_tuple(st, action, is_me):
        # st = (mx, my, md, mhp, mbhp, ox, oy, od, ohp, obhp)
        mx, my, md, mhp, mbhp, ox, oy, od, ohp, obhp = st
        if is_me:
            nx, ny, nd, nhp, nbhp = mx, my, md, mhp, mbhp
            target_hp, target_bhp, target_x, target_y = ohp, obhp, ox, oy
            t_base_x, t_base_y = opp_base["x"], opp_base["y"]
            my_base_x, my_base_y = my_base["x"], my_base["y"]
        else:
            nx, ny, nd, nhp, nbhp = ox, oy, od, ohp, obhp
            target_hp, target_bhp, target_x, target_y = mhp, mbhp, mx, my
            t_base_x, t_base_y = my_base["x"], my_base["y"]
            my_base_x, my_base_y = opp_base["x"], opp_base["y"]
            
        if action.startswith("MOVE_"):
            nd = action.replace("MOVE_", "")
            vx, vy = DIR_VECTORS[nd]
            tx, ty = nx + vx, ny + vy
            if 0 <= tx < grid_size and 0 <= ty < grid_size:
                if (tx, ty) not in obstacles and grid_map[ty][tx] != 2:
                    nx, ny = tx, ty
        elif action == "SHOOT":
            vx, vy = DIR_VECTORS[nd]
            cx, cy = nx + vx, ny + vy
            hit = False
            while 0 <= cx < grid_size and 0 <= cy < grid_size and not hit:
                if cx == target_x and cy == target_y:
                    target_hp -= 1
                    hit = True
                elif cx == t_base_x and cy == t_base_y:
                    target_bhp -= 1
                    hit = True
                elif cx == my_base_x and cy == my_base_y:
                    nbhp -= 1
                    hit = True
                elif (cx, cy) in obstacles:
                    hit = True
                elif grid_map[cy][cx] == 2:
                    hit = True
                cx += vx
                cy += vy
                
        if is_me:
            return (nx, ny, nd, nhp, nbhp, ox, oy, od, target_hp, target_bhp)
        else:
            return (mx, my, md, target_hp, target_bhp, nx, ny, nd, nhp, nbhp)

    initial_state = (
        my_tank["x"], my_tank["y"], my_tank["direction"], my_tank["hp"], my_base["hp"],
        opp_x, opp_y, opp_dir, opp_tank["hp"], opp_base["hp"]
    )
    
    root = Node(initial_state)

    def is_terminal(st):
        _, _, _, mhp, mbhp, _, _, _, ohp, obhp = st
        return mhp <= 0 or mbhp <= 0 or ohp <= 0 or obhp <= 0

    def evaluate_terminal(st):
        _, _, _, mhp, mbhp, _, _, _, ohp, obhp = st
        if ohp <= 0 or obhp <= 0:
            return 1.0 # Win
        if mhp <= 0 or mbhp <= 0:
            return 0.0 # Loss
        return 0.5 # Draw

    iterations = 0
    # Run MCTS until time limit
    while time.time() - start_time < TIME_LIMIT:
        iterations += 1
        node = root
        
        # 1. Selection
        while not node.untried_actions and node.children:
            node = max(node.children, key=lambda c: c.ucb1())
            
        # 2. Expansion
        if node.untried_actions and not is_terminal(node.state):
            action = random.choice(node.untried_actions)
            node.untried_actions.remove(action)
            # Apply our action
            temp_state = simulate_action_tuple(node.state, action, True)
            # Apply random opponent action (simultaneous simplification)
            opp_action = random.choice(["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "SHOOT", "IDLE"])
            next_state = simulate_action_tuple(temp_state, opp_action, False)
            
            new_node = Node(next_state, parent=node, action=action)
            node.children.append(new_node)
            node = new_node
            
        # 3. Simulation
        current_state = node.state
        sim_depth = 0
        while not is_terminal(current_state) and sim_depth < 10:
            my_act = random.choice(["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "SHOOT", "IDLE"])
            opp_act = random.choice(["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "SHOOT", "IDLE"])
            current_state = simulate_action_tuple(current_state, my_act, True)
            current_state = simulate_action_tuple(current_state, opp_act, False)
            sim_depth += 1
            
        # 4. Backpropagation
        result = evaluate_terminal(current_state)
        # If not terminal, use a heuristic evaluation
        if sim_depth == 10 and not is_terminal(current_state):
            mx, my, _, mhp, mbhp, ox, oy, _, ohp, obhp = current_state
            # Simple heuristic scaled between 0 and 1
            score = (mhp - ohp) * 0.1 + (mbhp - obhp) * 0.05
            result = max(0.0, min(1.0, 0.5 + score))

        while node is not None:
            node.visits += 1
            node.wins += result
            node = node.parent

    # Choose best child
    if not root.children:
        return "IDLE"
        
    best_child = max(root.children, key=lambda c: c.visits)
    print(f"[MCTS] Performed {iterations} iterations. Chosen action: {best_child.action}")
    return best_child.action
