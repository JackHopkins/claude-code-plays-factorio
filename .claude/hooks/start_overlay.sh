#!/bin/bash
# Hook to start the Factorio overlay server when Claude Code session starts

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(dirname $(dirname "$SCRIPT_DIR"))}"

# Log file for debugging
LOG_FILE="/tmp/factorio_overlay_hook.log"
PID_FILE="/tmp/factorio_overlay.pid"

echo "[$(date)] SessionStart hook triggered" >> "$LOG_FILE"
echo "[$(date)] Project root: $PROJECT_ROOT" >> "$LOG_FILE"

# Clean up any existing overlay processes
echo "[$(date)] Checking for existing overlay processes..." >> "$LOG_FILE"

# First try to kill using saved PID file
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    echo "[$(date)] Found saved PID: $OLD_PID" >> "$LOG_FILE"
    
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "[$(date)] Killing old overlay process (PID: $OLD_PID)..." >> "$LOG_FILE"
        kill $OLD_PID
        sleep 2
        
        # Force kill if still running
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "[$(date)] Force killing old overlay process..." >> "$LOG_FILE"
            kill -9 $OLD_PID
        fi
    fi
    rm -f "$PID_FILE"
fi

# Also kill any overlay.py processes that might be running
if pgrep -f "overlay_mcp.py" > /dev/null; then
    echo "[$(date)] Found overlay_mcp.py processes, killing them..." >> "$LOG_FILE"
    pkill -f "overlay_mcp.py"
    sleep 2
    
    # Force kill if still running
    if pgrep -f "overlay_mcp.py" > /dev/null; then
        echo "[$(date)] Force killing remaining overlay_mcp.py processes..." >> "$LOG_FILE"
        pkill -9 -f "overlay_mcp.py"
    fi
fi

# Now start a fresh overlay server
echo "[$(date)] Starting fresh overlay server..." >> "$LOG_FILE"

# Start the overlay server in the background
cd "$PROJECT_ROOT"
nohup python fle/overlay_mcp.py --port 8081 > /tmp/factorio_overlay.log 2>&1 &
OVERLAY_PID=$!

echo "[$(date)] Overlay started with PID: $OVERLAY_PID" >> "$LOG_FILE"

# Save PID for later cleanup
echo $OVERLAY_PID > "$PID_FILE"

# Give it a moment to start
sleep 2

# Verify it's running
if ps -p $OVERLAY_PID > /dev/null 2>&1; then
    echo "[$(date)] Overlay server successfully started" >> "$LOG_FILE"
    # Browser auto-opens from NiceGUI, no need to open manually
    # open "http://localhost:8081"
else
    echo "[$(date)] ERROR: Overlay server failed to start" >> "$LOG_FILE"
fi

echo "[$(date)] Hook completed" >> "$LOG_FILE"