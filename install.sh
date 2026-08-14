#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${AGENT_SKILLS_DIR:-$HOME/.agents/skills}"

SKILLS=(
  "run-parallel-city-adventure"
  "play-story-reflection-cards"
)

mkdir -p "$TARGET_DIR"

installed=0
skipped=0

for skill in "${SKILLS[@]}"; do
  source_dir="$REPO_DIR/skills/$skill"
  target_dir="$TARGET_DIR/$skill"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    echo "Missing source skill: $source_dir" >&2
    exit 1
  fi

  if [[ -e "$target_dir" ]]; then
    echo "Skip existing skill: $skill"
    skipped=$((skipped + 1))
    continue
  fi

  cp -R "$source_dir" "$target_dir"
  echo "Installed: $skill"
  installed=$((installed + 1))
done

echo
echo "Done. Installed $installed skill(s); skipped $skipped existing skill(s)."
echo "Open or refresh the Skills page to view them."

