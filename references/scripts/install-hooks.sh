#!/usr/bin/env bash
# install-hooks.sh — 手动安装/更新 git hooks
# 用法：bash processes/scripts/install-hooks.sh

set -euo pipefail
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo "")
[ -z "$GIT_DIR" ] && echo "错误：不在 git 仓库中" && exit 1

HOOK="$GIT_DIR/hooks/pre-push"

if [ -f "$HOOK" ]; then
  echo "pre-push hook 已存在，如需覆盖请手动删除后重新运行。"
  echo "当前 hook：$HOOK"
  exit 0
fi

# 从 SKILL.md 读取模板写入 hook（由 Agent 在 init 时直接写入，此脚本为备用手动路径）
cat > "$HOOK" << 'HOOK_EOF'
# [pre-push hook 内容由 /knowledge-wiki init 写入]
HOOK_EOF

chmod +x "$HOOK"
echo "✓ pre-push hook 已安装：$HOOK"
