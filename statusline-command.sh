#!/bin/sh
# Claude Code status line — robbyrussell style
input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
dir=$(basename "$cwd")
model=$(echo "$input" | jq -r '.model.display_name // ""')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Git branch (skip optional lock)
branch=""
if git -C "$cwd" rev-parse --git-dir > /dev/null 2>&1; then
  branch=$(git -C "$cwd" -c gc.auto=0 symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
  dirty=""
  if ! git -C "$cwd" diff --quiet 2>/dev/null || ! git -C "$cwd" diff --cached --quiet 2>/dev/null; then
    dirty=" ✗"
  fi
fi

# Build output with ANSI colors
if [ -n "$branch" ]; then
  git_part=$(printf " \033[1;34mgit:(\033[0;31m%s\033[1;34m)\033[0;33m%s\033[0m" "$branch" "$dirty")
else
  git_part=""
fi

dir_part=$(printf "\033[0;36m%s\033[0m" "$dir")

ctx_part=""
if [ -n "$used" ]; then
  ctx_part=$(printf " \033[2mctx:%.0f%%\033[0m" "$used")
fi

model_part=""
if [ -n "$model" ]; then
  model_part=$(printf " \033[2m%s\033[0m" "$model")
fi

cost_part=""
sess_pct=""
wk_pct=""
if [ -n "$CLAUDE_SESSION_COST_USD" ] && [ -n "$CLAUDE_SESSION_COST_LIMIT_USD" ]; then
  sess_pct=$(awk "BEGIN { printf \"%.0f\", ($CLAUDE_SESSION_COST_USD / $CLAUDE_SESSION_COST_LIMIT_USD) * 100 }")
fi
if [ -n "$CLAUDE_WEEKLY_COST_USD" ] && [ -n "$CLAUDE_WEEKLY_COST_LIMIT_USD" ]; then
  wk_pct=$(awk "BEGIN { printf \"%.0f\", ($CLAUDE_WEEKLY_COST_USD / $CLAUDE_WEEKLY_COST_LIMIT_USD) * 100 }")
fi
if [ -n "$sess_pct" ] && [ -n "$wk_pct" ]; then
  cost_part=$(printf " \033[2msess:%s%% | wk:%s%%\033[0m" "$sess_pct" "$wk_pct")
elif [ -n "$sess_pct" ]; then
  cost_part=$(printf " \033[2msess:%s%%\033[0m" "$sess_pct")
elif [ -n "$wk_pct" ]; then
  cost_part=$(printf " \033[2mwk:%s%%\033[0m" "$wk_pct")
fi

printf "%s%s%s%s%s" "$dir_part" "$git_part" "$ctx_part" "$model_part" "$cost_part"
