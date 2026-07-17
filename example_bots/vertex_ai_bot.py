"""
Vertex AI LLM Bot for Tank Battle 2D
====================================
This bot uses Google Cloud Vertex AI to reason about the game state
and decide the best move each turn.

KEY DESIGN: The Python code pre-computes which moves are LEGAL and what
each direction contains, then only presents valid options to the LLM.
The LLM's choice is validated before returning — it can NEVER make an
illegal move.

SETUP: 
1. Set your Google Cloud PROJECT_ID and LOCATION (e.g., "us-central1").
2. Generate an OAuth access token (e.g., using `gcloud auth print-access-token`)
3. Paste the token into the ACCESS_TOKEN variable. Note that this token will expire!
"""

import json

# ============================================================
# PASTE YOUR VERTEX AI CREDENTIALS BELOW
# ============================================================
PROJECT_ID = ""
LOCATION = "us-central1"
ACCESS_TOKEN = ""
# ============================================================

MODEL = "gemini-2.5-flash"

# ============================================================
# GAME LOGIC HELPERS (Python, not LLM)
# ============================================================

CELL_NAMES = {
    0: "Empty",
    1: "Steel Wall (INDESTRUCTIBLE - cannot enter, cannot destroy)",
    2: "Brick Wall (destructible - can shoot to destroy, cannot enter)",
    3: "Bush (can enter, provides concealment)",
    4: "Fuel Canister (can enter, gives +10 fuel)",
}
PASSABLE = {0, 3, 4}  # cells a tank can move into
BLOCKING = {1, 2}     # cells that block bullets

DIRECTIONS = {
    "MOVE_UP":    (0, -1, "UP"),
    "MOVE_DOWN":  (0,  1, "DOWN"),
    "MOVE_LEFT":  (-1, 0, "LEFT"),
    "MOVE_RIGHT": (1,  0, "RIGHT"),
}

def get_cell(state, x, y):
    """Return the cell type at (x,y) or -1 if out of bounds."""
    gs = state["grid_size"]
    if x < 0 or x >= gs or y < 0 or y >= gs:
        return -1
    return state["map"][y][x]

def is_base(state, x, y):
    """Check if (x,y) is any base."""
    mb = state["my_base"]
    ob = state["opponent_base"]
    return (x == mb["x"] and y == mb["y"]) or (x == ob["x"] and y == ob["y"])

def compute_valid_moves(state):
    """Return a dict of {action: description} for all LEGAL moves."""
    my = state["my_tank"]
    mx, my_y = my["x"], my["y"]
    fuel = my["fuel"]
    valid = {}

    # IDLE is always valid
    valid["IDLE"] = "Do nothing this turn."

    if fuel <= 0:
        return valid  # No fuel, only IDLE

    # Check each movement direction
    for action, (dx, dy, _dir_name) in DIRECTIONS.items():
        nx, ny = mx + dx, my_y + dy
        cell = get_cell(state, nx, ny)
        if cell in PASSABLE and not is_base(state, nx, ny):
            cell_desc = CELL_NAMES.get(cell, "Unknown")
            valid[action] = f"Move to ({nx},{ny}) which is: {cell_desc}."
        # If not passable, we simply don't include it as an option

    # Check SHOOT — trace the line of sight
    facing = my["direction"]
    dx, dy = 0, 0
    if facing == "UP": dy = -1
    elif facing == "DOWN": dy = 1
    elif facing == "LEFT": dx = -1
    elif facing == "RIGHT": dx = 1

    if dx != 0 or dy != 0:
        sx, sy = mx + dx, my_y + dy
        dist = 1
        while 0 <= sx < state["grid_size"] and 0 <= sy < state["grid_size"]:
            # Check opponent tank
            ot = state["opponent_tank"]
            if ot["x"] is not None and sx == ot["x"] and sy == ot["y"]:
                valid["SHOOT"] = f"EXCELLENT! Your bullet will hit the ENEMY TANK at ({sx},{sy}), {dist} cells away!"
                break
            # Check opponent base
            ob = state["opponent_base"]
            if sx == ob["x"] and sy == ob["y"]:
                valid["SHOOT"] = f"EXCELLENT! Your bullet will hit the ENEMY BASE at ({sx},{sy}), {dist} cells away!"
                break
            # Check own base
            mb = state["my_base"]
            if sx == mb["x"] and sy == mb["y"]:
                # DO NOT offer SHOOT — would hit own base
                break
            # Check walls
            cell = get_cell(state, sx, sy)
            if cell == 1:
                # Steel wall — shooting is wasteful, don't offer it
                break
            if cell == 2:
                valid["SHOOT"] = f"Your bullet will destroy a Brick Wall at ({sx},{sy}), {dist} cells away, opening a path."
                break
            sx += dx
            sy += dy
            dist += 1
        # If we exited the loop without breaking, bullet flies off map — don't offer SHOOT

    return valid

def build_local_map(state):
    """Build a compact text representation of the area around the tank."""
    my_x = state["my_tank"]["x"]
    my_y = state["my_tank"]["y"]
    grid_map = state["map"]
    grid_size = state["grid_size"]
    
    SYMBOLS = {0: ".", 1: "#", 2: "B", 3: "~", 4: "F"}
    
    radius = 6
    lines = []
    for dy in range(-radius, radius + 1):
        row = []
        for dx in range(-radius, radius + 1):
            x, y = my_x + dx, my_y + dy
            if x < 0 or x >= grid_size or y < 0 or y >= grid_size:
                row.append("X")
            elif x == my_x and y == my_y:
                row.append("T")
            elif x == state["my_base"]["x"] and y == state["my_base"]["y"]:
                row.append("H")
            elif x == state["opponent_base"]["x"] and y == state["opponent_base"]["y"]:
                row.append("E")
            elif state["opponent_tank"]["x"] is not None and x == state["opponent_tank"]["x"] and y == state["opponent_tank"]["y"]:
                row.append("O")
            else:
                row.append(SYMBOLS.get(grid_map[y][x], "?"))
        lines.append(" ".join(row))
    
    return "\n".join(lines)

def build_prompt(state, valid_moves):
    my = state["my_tank"]
    opp = state["opponent_tank"]
    my_base = state["my_base"]
    opp_base = state["opponent_base"]
    
    opp_x_str = str(opp["x"]) if opp["x"] is not None else "HIDDEN (in bush)"
    opp_y_str = str(opp["y"]) if opp["y"] is not None else "HIDDEN (in bush)"
    opp_dir_str = opp["direction"] if opp["direction"] is not None else "UNKNOWN"

    local_map = build_local_map(state)
    
    # Format valid moves as a numbered list
    moves_text = ""
    for action, desc in valid_moves.items():
        moves_text += f"  - {action}: {desc}\n"

    # Recent history
    my_hist = state.get("my_history", [])[:5]
    opp_hist = state.get("opponent_history", [])[:5]
    my_hist_str = ", ".join([f"T{h['turn']}:{h['action']}" for h in my_hist]) if my_hist else "None"
    opp_hist_str = ", ".join([f"T{h['turn']}:{h['action']}" for h in opp_hist]) if opp_hist else "None"

    prompt = f"""TURN {state['turn']}

MY TANK: pos=({my['x']},{my['y']}) facing={my['direction']} hp={my['hp']} fuel={my['fuel']}
MY BASE: pos=({my_base['x']},{my_base['y']}) hp={my_base['hp']}
ENEMY TANK: pos=({opp_x_str},{opp_y_str}) facing={opp_dir_str} hp={opp['hp']} fuel={opp['fuel']}
ENEMY BASE: pos=({opp_base['x']},{opp_base['y']}) hp={opp_base['hp']}

LOCAL MAP (T=me, O=opponent, H=my base, E=enemy base, #=steel wall, B=brick wall, ~=bush, F=fuel, .=empty):
{local_map}

YOUR LEGAL MOVES THIS TURN (you MUST pick one of these):
{moves_text}
MY RECENT MOVES: {my_hist_str}
ENEMY RECENT MOVES: {opp_hist_str}

Pick the best action from YOUR LEGAL MOVES. Your goal is to destroy the enemy base (E) or enemy tank (O). Keep your thought very short (1 sentence max)."""

    return prompt

# ============================================================
# SYSTEM PROMPT (simplified — game logic is handled by Python)
# ============================================================

SYSTEM_PROMPT = """You are a tank commander AI. You will be given the game state and a list of LEGAL MOVES.

RULES:
- You MUST pick an action from the provided LEGAL MOVES list. No other actions exist.
- If SHOOT is listed, it means your bullet WILL hit something useful. Take the shot!
- Your goal: destroy the enemy base (E) or enemy tank (O).
- Strategy: move toward the enemy base, shoot when aligned, avoid wasting turns.
- Keep your "thought" to 1 short sentence. Be decisive."""

async def get_move(state):
    from pyodide.http import pyfetch
    
    if PROJECT_ID == "YOUR_PROJECT_ID" or ACCESS_TOKEN == "YOUR_ACCESS_TOKEN":
        print("[VERTEX AI BOT] ERROR: Setup incomplete! Edit vertex_ai_bot.py and set PROJECT_ID and ACCESS_TOKEN.")
        return "IDLE"

    # Step 1: Compute valid moves in Python (guaranteed correct)
    valid_moves = compute_valid_moves(state)
    valid_actions = list(valid_moves.keys())
    
    print(f"[VERTEX AI BOT] Legal moves: {valid_actions}")
    
    # Step 2: If SHOOT is available and it hits enemy base or tank, just do it!
    if "SHOOT" in valid_moves:
        desc = valid_moves["SHOOT"]
        if "ENEMY TANK" in desc or "ENEMY BASE" in desc:
            print(f"[VERTEX AI BOT] 💭 Auto-shoot: {desc}")
            print(f"[VERTEX AI BOT] ⚡ Action: SHOOT")
            return "SHOOT"
    
    # Step 3: If only IDLE is available, skip the API call
    if valid_actions == ["IDLE"]:
        print("[VERTEX AI BOT] 💭 No fuel remaining, forced IDLE.")
        print("[VERTEX AI BOT] ⚡ Action: IDLE")
        return "IDLE"
    
    # Step 4: Ask the LLM to pick from ONLY the valid moves
    prompt = build_prompt(state, valid_moves)
    
    url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "thought": {
                        "type": "STRING",
                        "description": "One short sentence of reasoning"
                    },
                    "action": {
                        "type": "STRING",
                        "description": "The chosen action",
                        "enum": valid_actions
                    }
                },
                "required": ["thought", "action"]
            }
        }
    }
    
    try:
        print(f"[VERTEX AI BOT] Calling Vertex AI ({MODEL})...")
        
        response = await pyfetch(
            url,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            },
            body=json.dumps(payload)
        )
        
        response_text = await response.string()
        
        if response.status != 200:
            print(f"[VERTEX AI BOT] API Error {response.status}: {response_text[:500]}")
            # Fallback: pick first non-IDLE move
            for a in valid_actions:
                if a != "IDLE":
                    return a
            return "IDLE"
        
        result = json.loads(response_text)
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Clean markdown wrapping
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            parsed = json.loads(text)
            thought = parsed.get("thought", "")
            action = parsed.get("action", "IDLE").upper().strip()
        except json.JSONDecodeError:
            print(f"[VERTEX AI BOT] JSON parse failed: {text[:100]}...")
            import re
            match = re.search(r'"action"\s*:\s*"([A-Z_]+)"', text)
            action = match.group(1) if match else "IDLE"
            thought = "Truncated response"
        
        print(f"[VERTEX AI BOT] 💭 {thought}")
        print(f"[VERTEX AI BOT] ⚡ Action: {action}")
        
        # FINAL SAFETY: validate against computed legal moves
        if action in valid_actions:
            return action
        else:
            print(f"[VERTEX AI BOT] ⚠️ LLM chose '{action}' which is NOT legal! Picking best fallback.")
            # Pick first non-IDLE move
            for a in valid_actions:
                if a != "IDLE":
                    return a
            return "IDLE"
            
    except Exception as e:
        print(f"[VERTEX AI BOT] Exception: {type(e).__name__}: {str(e)[:500]}")
        for a in valid_actions:
            if a != "IDLE":
                return a
        return "IDLE"
