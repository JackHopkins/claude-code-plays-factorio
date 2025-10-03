# Claude Code Plays Factorio
This repository makes it easy for you to build your own Claude Code agents to play Factorio.

```shell
uv add factorio-learning-environment

fle cluster start -s open_world


```


## Overview
This project connects Claude AI to Factorio via the [Factorio Learning Environment](https://github.com/JackHopkins/factorio-learning-environment), allowing Claude to write and execute Python code to build factories, automate production lines, and solve complex engineering challenges in the game. Claude interacts with the game world through a resource-based API, making decisions and building increasingly sophisticated automated systems.

## How It Works
Claude operates as an expert automation engineer within Factorio's world of Nauvis. The system provides:

- **Code Execution:** Claude writes Python scripts to perform game actions
- **Resource Observation:** Real-time access to game state through REST-like resources
- **Version Control:** Git-like commit/restore system for rapid iteration and experimentation
- **Visualization:** Factory state rendering for debugging and monitoring
- **Persistent Memory:** Local workspace for maintaining knowledge between sessions

Architecture
┌─────────────────┐
│     Claude      │ Writes Python code
│   (AI Agent)    │ Makes decisions
└────────┬────────┘
         │
         ↓ MCP Protocol
┌─────────────────┐
│   FLE Server    │ Game state resources
│   (MCP Server)  │ Code execution
└────────┬────────┘
         │
         ↓ Lua API
┌─────────────────┐
│    Factorio     │ The actual game
│   Game Engine   │
└─────────────────┘
Key Components

Resources (fle://): Read-only access to game state (inventory, entities, position, etc.)
Tools: State-modifying actions (execute code, render views, version control)
Workspace: Local filesystem for documentation, notes, and learning patterns

API Overview
Resources (Observation)

fle://status - Connection status
fle://entities/{x}/{y}/{radius} - Entity information in area
fle://inventory - Current inventory
fle://position - Player position
fle://recipe/{name} - Recipe details
fle://metrics - Production statistics
fle://render/{x}/{y} - Visual factory state

Tools (Actions)

execute(code) - Run Python code
commit(tag, message) - Save game state
restore(ref) - Revert to previous state
render(x, y) - Generate visualization

Core Capabilities
Claude can:

Build Mining Operations: Automated ore extraction with self-fueling systems
Create Production Lines: Multi-stage processing from raw materials to finished goods
Manage Power Infrastructure: Steam engine setups with boilers and offshore pumps
Design Belt Systems: Complex logistics networks for material transport
Research Technology: Automated lab setups for unlocking new capabilities
Optimize Throughput: Calculate and implement efficient production ratios