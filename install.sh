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
    echo "缺少 Skill 源目录：$source_dir" >&2
    exit 1
  fi

  if [[ -e "$target_dir" ]]; then
    echo "已跳过现有 Skill：$skill"
    skipped=$((skipped + 1))
    continue
  fi

  cp -R "$source_dir" "$target_dir"
  echo "已安装：$skill"
  installed=$((installed + 1))
done

echo
echo "完成：安装 $installed 个 Skill；跳过 $skipped 个已存在的 Skill。"
echo "打开或刷新 Skills 页面即可查看。"
