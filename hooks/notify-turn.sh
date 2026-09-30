#!/bin/bash

CLAUDE_BUNDLE_ID="com.anthropic.claudefordesktop"
SUPPRESS_WHEN_FRONTMOST="${CLAUDE_NOTIFY_SUPPRESS:-1}"
NOTIFIER="$HOME/Applications/Claude Code Notifier.app/Contents/MacOS/terminal-notifier"

input=$(cat)

if [ "$SUPPRESS_WHEN_FRONTMOST" = "1" ] && command -v lsappinfo >/dev/null 2>&1; then
  front_asn=$(lsappinfo front 2>/dev/null)
  if [ -n "$front_asn" ]; then
    front_bid=$(lsappinfo info -only bundleid "$front_asn" 2>/dev/null | sed 's/.*=//; s/"//g')
    [ "$front_bid" = "$CLAUDE_BUNDLE_ID" ] && exit 0
  fi
fi

cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
project=$(basename "${cwd:-$PWD}")

transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
if [ -z "$transcript" ]; then
  session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
  if [ -n "$session_id" ] && [ -n "$cwd" ]; then
    transcript="$HOME/.claude/projects/$(printf '%s' "$cwd" | tr '/.' '--')/$session_id.jsonl"
  fi
fi

title=""
if [ -f "$transcript" ]; then
  title=$(grep '"type":"custom-title"' "$transcript" 2>/dev/null | tail -1 | jq -r '.customTitle // empty' 2>/dev/null)
fi
[ -z "$title" ] && title="$project"

message=$(printf '%s' "$input" | jq -r '.message // empty' 2>/dev/null)
[ -z "$message" ] && message="${1:-Your turn}"

sound="${2:-Glass}"
[ -f "/System/Library/Sounds/$sound.aiff" ] || sound="Glass"

notify() {
  "$1" \
    -title "$title" \
    -subtitle "$project" \
    -message "$message" \
    -sound "$sound" \
    -group "claude-code-$project" \
    -activate "$CLAUDE_BUNDLE_ID" >/dev/null 2>&1
}

if [ -x "$NOTIFIER" ]; then
  notify "$NOTIFIER"
elif command -v terminal-notifier >/dev/null 2>&1; then
  notify "$(command -v terminal-notifier)"
else
  osascript -e "display notification \"${message//\"/}\" with title \"${title//\"/}\" subtitle \"${project//\"/}\" sound name \"$sound\"" >/dev/null 2>&1
fi

exit 0
