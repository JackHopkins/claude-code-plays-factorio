#!/bin/bash
# auto_continue.sh - Fixed to handle Stop events properly

#/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.fle/sprites/alert-no-ammo.png
INPUT=$(cat)
LOG_FILE="/tmp/factorio_overlay_hook.log"

echo "[$(date)] Hook triggered" >> "$LOG_FILE"
echo "[$(date)] Raw input: $INPUT" >> "$LOG_FILE"

# Function to send to Claude Code tmux session
send_continue_to_tmux() {
    if tmux has-session -t claude-code 2>/dev/null; then
        echo "[$(date)] Found claude-code tmux session" >> "$LOG_FILE"

        # Send Continue with C-m (carriage return) for proper submission
        tmux send-keys -t claude-code "Observe your environment by accessing all available resources and then continue development" C-m
        tmux send-keys -t claude-code C-m

        echo "[$(date)] Sent 'Continue' with C-m to claude-code session" >> "$LOG_FILE"

        # Log last few lines for debugging
        tmux capture-pane -t claude-code -p | tail -5 >> "$LOG_FILE"

        return 0
    else
        echo "[$(date)] No claude-code tmux session found" >> "$LOG_FILE"
        return 1
    fi
}

# Parse the notification using jq
if command -v jq &> /dev/null; then
    HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // ""')
    MESSAGE=$(echo "$INPUT" | jq -r '.message // .content // ""')
    TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // ""')

    echo "[$(date)] Parsed - Event: $HOOK_EVENT, Message: $MESSAGE, Tool: $TOOL_NAME" >> "$LOG_FILE"

    # PRIMARY CHECK: If this is a Stop event, always send Continue
    if [ "$HOOK_EVENT" = "Stop" ]; then
        echo "[$(date)] Stop event detected - sending Continue" >> "$LOG_FILE"
        if send_continue_to_tmux; then
            echo '{"action": "continue", "response": "Observe your environment by accessing all available resources and then continue development"}'
            exit 0
        fi
    fi
    $CONTINUE = "Observe your environment by accessing all available resources and continue development"

    # Secondary check for message-based conditions (for other hook types)
    if [ -n "$MESSAGE" ]; then
        if echo "$MESSAGE" | grep -iE "(factorio.*complete|agent.*stopped|observation.*ready|waiting for input|Claude is waiting)" > /dev/null 2>&1; then
            echo "[$(date)] Auto-continue condition met in message" >> "$LOG_FILE"
            if send_continue_to_tmux; then
                echo '{"action": "continue", "response": "$CONTINUE"}'
                exit 0
            fi
        fi
    fi
fi

echo '{"action": "none"}'