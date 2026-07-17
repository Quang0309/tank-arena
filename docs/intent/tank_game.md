# Project Intent: AI Tank Game

## Overview
A strategy-focused 2D grid-based (24x24) simultaneous turn-based tank arena web app. The key selling point of this game is that tanks can be controlled either manually or by user-uploaded Python (`.py`) files, which are run client-side in the browser using Pyodide (Python in WebAssembly).

## Core Requirements

- **Outcome**: A web interface running entirely client-side. Players upload their Python scripts, which conform to a specific API/interface, to control their respective tanks.
- **User**: Developers, AI hobbyists, or students who want to test their algorithms and strategy models.
- **Success Criteria**:
  - A clean 2D game board (using CSS Grid or HTML5 Canvas).
  - Clear visual tracking of tank positions, base positions, and walls (destructible vs. indestructible).
  - Simple controls to upload P1 and P2 `.py` script files, start the simulation, control the speed, and reset the board.
  - A dashboard showing current stats: randomized starting HP for tanks/bases, remaining fuel, and turn numbers.
  - Symmetrical spawn logic for fairness.
- **Constraints**:
  - Run completely in the browser (client-side Pyodide). No backend server execution.
  - Simultaneous turns: both tanks take one action at the same time.
  - Action space: Move (Up/Down/Left/Right), Shoot (Up/Down/Left/Right), or Idle.
  - Fuel consumption: Move/Shoot costs 1 fuel, Idle costs 0 fuel. Tanks cannot act when out of fuel.
- **Out of Scope**:
  - 3D rendering or complex animations.
  - Online multiplayer network matchmaking.
  - Server-side database or leaderboards.
