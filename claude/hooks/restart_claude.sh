#!/bin/bash
# restart_claude.sh - Run normally

echo "Restarting Claude Code with updated hooks..."

# Kill existing session
tmux kill-session -t claude-code 2>/dev/null
pkill -f "claude code" 2>/dev/null

sleep 1

# Start normally
tmux new-session -d -s claude-code 'claude code'

# Attach
tmux attach -t claude-code