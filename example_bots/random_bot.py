import random

def get_move(state):
    """
    Random Bot - Strategy: Wander around randomly and shoot occasionally.
    """
    actions = [
        "MOVE_UP", 
        "MOVE_DOWN", 
        "MOVE_LEFT", 
        "MOVE_RIGHT", 
        "SHOOT", 
        "IDLE"
    ]
    
    # 50% chance to move, 30% chance to shoot, 20% chance to idle
    weights = [0.125, 0.125, 0.125, 0.125, 0.3, 0.2]
    
    return random.choices(actions, weights=weights)[0]
