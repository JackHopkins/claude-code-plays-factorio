#!/bin/bash
# start_claude_clean.sh - Start Claude Code with fresh hooks

LOG_FILE="/tmp/factorio_overlay_hook.log"
echo "[$(date)] Starting Claude Code with clean reload..." >> "$LOG_FILE"
CLAUDE_PROJECT_DIR="/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.claude-code"
# Function to kill all Claude-related processes
cleanup_claude() {
    echo "Cleaning up existing Claude processes..."

    # Kill tmux session if exists
    if tmux has--t claude-code 2>/dev/null; then
        echo "  - Killing existing tmux session 'claude-code'"
        tmux kill-session -t claude-code
        sleep 1
    fi

    # Kill any Claude Code processes directly
    if pgrep -f "claude code" > /dev/null; then
        echo "  - Killing Claude Code processes"
        pkill -f "claude code"
        sleep 2

        # Force kill if still running
        if pgrep -f "claude code" > /dev/null; then
            echo "  - Force killing remaining processes"
            pkill -9 -f "claude code"
            sleep 1
        fi
    fi

    # Kill any orphaned node processes from Claude
    if pgrep -f "claude.*node" > /dev/null; then
        echo "  - Killing orphaned node processes"
        pkill -f "claude.*node"
    fi

    echo "Cleanup complete"
}

# Function to verify hooks are in place
verify_hooks() {
    echo "Verifying hook files..."

    HOOKS_DIR="$CLAUDE_PROJECT_DIR/.claude/hooks"
    echo $HOOKS_DIR
    # Check auto_continue.sh
    if [ -f "$HOOKS_DIR/auto_continue.sh" ]; then
        echo "  ✓ auto_continue.sh found"
        chmod +x "$HOOKS_DIR/auto_continue.sh"
    else
        echo "  ✗ auto_continue.sh missing!"
        return 1
    fi

    # Check settings.json
    if [ -f "$CLAUDE_PROJECT_DIR/.claude/settings.json" ]; then
        echo "  ✓ settings.json found"
    else
        echo "  ✗ settings.json missing!"
        return 1
    fi

    return 0
}

# Main execution
echo "=== Claude Code Clean Start ==="

# 1. Clean up existing processes
cleanup_claude

# 2. Verify hooks are in place
if ! verify_hooks; then
    echo "ERROR: Hook files not properly configured"
    exit 1
fi

# 3. Clear any stale logs
echo "[$(date)] === Fresh session start ===" > "$LOG_FILE"

# 4. Export environment variables for hooks
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
echo "Project directory: $CLAUDE_PROJECT_DIR"

# 5. Start Claude Code in tmux
echo "Starting fresh Claude Code session..."
tmux new-session -d -s claude-code "
    echo 'Claude Code session starting...'
    echo 'Project: $CLAUDE_PROJECT_DIR'
    echo 'Hooks will auto-reload from .claude/hooks/'
    echo ''
    claude code
"

# 6. Wait for it to initialize
echo "Waiting for Claude Code to initialize..."
sleep 3

# 7. Verify it started
if tmux has-session -t claude-code 2>/dev/null; then
    echo ""
    echo "✅ Claude Code started successfully!"
    echo ""
    echo "Session: claude-code"
    echo "Hooks: Loaded from $CLAUDE_PROJECT_DIR/.claude/hooks/"
    echo "Logs: tail -f $LOG_FILE"
    echo ""
    echo "Attaching to session..."
    echo "(Press Ctrl+B then D to detach)"
    echo ""

    # Attach to the session
    tmux attach -t claude-code
else
    echo "❌ Failed to start Claude Code"
    echo "Check logs at: $LOG_FILE"
    exit 1
fi