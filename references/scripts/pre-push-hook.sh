#!/usr/bin/env bash
# pre-push hook — 推送前检查知识库同步状态
# 由 /knowledge-wiki init 自动生成，勿手动删除
# 临时跳过：git push --no-verify

set -euo pipefail

BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RESET="\033[0m"

# 读取 push 目标（git 通过 stdin 传入）
read -r LOCAL_REF LOCAL_SHA REMOTE_REF REMOTE_SHA || true

# 确定对比基准
ZERO_SHA="0000000000000000000000000000000000000000"
if [ "$REMOTE_SHA" = "$ZERO_SHA" ]; then
  BASE_REF=$(git rev-parse --verify origin/main 2>/dev/null || \
             git rev-parse --verify origin/master 2>/dev/null || \
             git rev-parse --verify HEAD~1 2>/dev/null || echo "")
else
  BASE_REF="$REMOTE_SHA"
fi

[ -z "$BASE_REF" ] && exit 0

# ── 路径 A：自动生成 generated/ 和 dashboard.md ──────────────────
# 在检查之前先刷新生成文件，确保 push 的内容是最新的
GENERATE_DOCS="processes/scripts/generate-docs.sh"
GENERATE_DASH="processes/scripts/generate-dashboard.py"

if [ -f "$GENERATE_DOCS" ]; then
  echo "  → 刷新 docs/generated/ ..."
  bash "$GENERATE_DOCS" --all 2>/dev/null || true
fi

if [ -f "$GENERATE_DASH" ] && command -v python3 &>/dev/null; then
  echo "  → 刷新 dashboard.md ..."
  python3 "$GENERATE_DASH" 2>/dev/null || true
fi

# 如果有生成文件变更，自动暂存（让它们随本次 push 一起上去）
if git diff --quiet .knowledge/docs/generated/ .knowledge/dashboard.md 2>/dev/null; then
  : # 无变化，跳过
else
  git add .knowledge/docs/generated/ .knowledge/dashboard.md 2>/dev/null || true
  echo "  ✓ 生成文件已暂存"
fi

HAS_ISSUE=0

# ── 检查一：同步源陈旧检测 ──────────────────────────────────────
SOURCES_FILE=".knowledge/.kb-meta/sources.json"
if [ -f "$SOURCES_FILE" ]; then
  # 找出 status=stale 或 status=error 的源
  STALE_SOURCES=$(python3 -c "
import json, sys
data = json.load(open('$SOURCES_FILE'))
bad = [s for s in data.get('sources', []) if s.get('status') in ('stale','error')]
if bad:
    print('\n⚠  发现未同步的知识源：')
    for s in bad:
        icon = '🔴' if s['status'] == 'error' else '⏰'
        print(f\"  {icon} [{s['id']}] {s['name']} ({s['status']}, 上次同步: {s.get('last_synced','从未')})\")
    sys.exit(1)
" 2>/dev/null || echo "")

  if [ -n "$STALE_SOURCES" ]; then
    echo -e "${YELLOW}${STALE_SOURCES}${RESET}"
    echo "   建议运行：/knowledge-wiki source sync"
    HAS_ISSUE=1
  fi
fi

# ── 检查二：代码变更 → 文档映射 ─────────────────────────────────
SYNC_SCRIPT="processes/scripts/kb-sync.sh"
CODE_ISSUE=0
if [ -f "$SYNC_SCRIPT" ]; then
  if ! bash "$SYNC_SCRIPT" "$BASE_REF"; then
    CODE_ISSUE=1
    HAS_ISSUE=1
  fi
fi

# 无问题直接放行
if [ "$HAS_ISSUE" -eq 0 ]; then
  echo -e "${GREEN}✓ 知识库无需更新，继续推送。${RESET}"
  exit 0
fi

# ── 询问用户 ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}检测到知识库有待处理事项，如何继续？${RESET}"
echo "  [1] 先同步知识源（/knowledge-wiki source sync）后重新 push"
echo "  [2] 先更新文档页面（/knowledge-wiki wiki）后重新 push"
echo "  [3] 两者都做后重新 push"
echo "  [4] 跳过，直接推送"
printf "请选择 [1/2/3/4，默认 4]: "

CHOICE=""
read -r CHOICE < /dev/tty 2>/dev/null || true

case "${CHOICE:-4}" in
  1)
    echo -e "\n${YELLOW}⏸  推送已中止。${RESET}"
    echo "   请运行：/knowledge-wiki source sync && git push"
    exit 1 ;;
  2)
    echo -e "\n${YELLOW}⏸  推送已中止。${RESET}"
    echo "   请运行：/knowledge-wiki wiki && git push"
    exit 1 ;;
  3)
    echo -e "\n${YELLOW}⏸  推送已中止。${RESET}"
    echo "   请运行：/knowledge-wiki source sync && /knowledge-wiki wiki && git push"
    exit 1 ;;
  *)
    echo -e "\n${GREEN}→  跳过，继续推送。${RESET}"
    exit 0 ;;
esac
