# Game Vision

## Elevator Pitch

RiveRaid is based on 8-bit Atari River Radi arcade game. Main purpose is to explore real time system design, and the game is just a side effect

## Core Fantasy

- Fly a plane through procedurally generated river levels
- Levels are separated by bridges; cross a bridge to advance
- Refuel the plane at fuel stations as you fly — run out and crash
- Tank enemies on the river banks shoot horizontal missiles at the player
- Helicopter groups patrol over the water; group size grows with each level
- Fast jets cross the river horizontally at higher levels

## Design Pillars

1. **Realtime Piloting and Combat**
   - Flight and combat are skill-based in 2D realtime.
   - Score by shooting enemy vehicles, fuel stations, and bridges.
   - Enemy difficulty scales per level: larger helicopter groups, higher spawn density, jets at level 3.

## Initial Constraints

- Web-based client.
- Python backend.
- 2D simulation and rendering.
- Procedurally generated river
