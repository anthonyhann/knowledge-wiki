#!/usr/bin/env bash
# kb-sync.sh — 分析 git 变更，识别需要更新的 .knowledge/ 文档
# 用法：bash processes/scripts/kb-sync.sh [base_ref]
# base_ref 默认 HEAD~1，pre-push hook 会传入 origin/branch

set -euo pipefail

BASE_REF="${1:-HEAD~1}"
KB_DIR=".knowledge"
BOLD="\033[1m"
YELLOW="\033[33m"
GREEN="\033[32m"
CYAN="\033[36m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}━━━ 知识库同步分析 (.knowledge/) ━━━${RESET}"
echo ""

# ── 1. 获取本次变更的文件列表 ──────────────────────────────────────
CHANGED_FILES=$(git diff --name-only "${BASE_REF}" HEAD 2>/dev/null || git diff --name-only --cached 2>/dev/null || echo "")

if [ -z "$CHANGED_FILES" ]; then
  echo "  无代码变更，跳过知识库同步分析。"
  exit 0
fi

echo -e "${CYAN}📦 本次变更文件：${RESET}"
echo "$CHANGED_FILES" | sed 's/^/  /'
echo ""

# ── 2. 规则映射：代码变更 → 知识库文档 ────────────────────────────
declare -A AFFECTED_DOCS
declare -A REASONS

_mark() {
  local doc="$1" reason="$2"
  AFFECTED_DOCS["$doc"]=1
  REASONS["$doc"]+="  · ${reason}\n"
}

while IFS= read -r f; do
  [ -z "$f" ] && continue

  # skill SKILL.md 变更 → 对应技能实体页
  if [[ "$f" =~ ^([^/]+)/SKILL\.md$ ]]; then
    skill="${BASH_REMATCH[1]}"
    _mark "pages/entities/${skill}.md" "技能定义变更：${f}"
  fi

  # README 变更 → 对应实体页
  if [[ "$f" =~ ^([^/]+)/README\.md$ ]]; then
    skill="${BASH_REMATCH[1]}"
    _mark "pages/entities/${skill}.md" "README 变更：${f}"
  fi

  # CHANGELOG 变更 → 对应实体页（版本信息需同步）
  if [[ "$f" =~ ^([^/]+)/CHANGELOG\.md$ ]]; then
    skill="${BASH_REMATCH[1]}"
    _mark "pages/entities/${skill}.md" "CHANGELOG 变更：${f}"
  fi

  # 代码文件变更 → 对应模块文档
  if [[ "$f" =~ \.(go|py|ts|js|php|java|rs)$ ]]; then
    dir=$(dirname "$f" | cut -d'/' -f1)
    if [ -n "$dir" ] && [ "$dir" != "." ]; then
      _mark "pages/entities/${dir}.md" "源码变更：${f}"
    fi
  fi

  # processes/ 变更 → 流程文档
  if [[ "$f" =~ ^processes/ ]]; then
    _mark "pages/processes/workflow.md" "流程脚本变更：${f}"
  fi

  # .knowledge/ 自身变更不触发循环（跳过）
done <<< "$CHANGED_FILES"

# ── 3. 输出建议更新的文档 ──────────────────────────────────────────
if [ ${#AFFECTED_DOCS[@]} -eq 0 ]; then
  echo -e "${GREEN}✓ 未检测到需要同步的知识库文档。${RESET}"
  echo ""
  exit 0
fi

echo -e "${YELLOW}📝 建议更新以下知识库文档：${RESET}"
echo ""

for doc in "${!AFFECTED_DOCS[@]}"; do
  if [ -f "${KB_DIR}/${doc}" ]; then
    exists=" ${GREEN}[已存在，需更新]${RESET}"
  else
    exists=" ${YELLOW}[待创建]${RESET}"
  fi
  echo -e "  ${BOLD}${doc}${RESET}${exists}"
  printf "%b" "${REASONS[$doc]}"
  echo ""
done

# ── 4. 检查 .knowledge/ 目录 ──────────────────────────────────────
if [ ! -d "$KB_DIR" ]; then
  echo -e "${YELLOW}⚠  .knowledge/ 目录不存在，可运行 /knowledge-wiki init 初始化。${RESET}"
  echo ""
fi

echo -e "${CYAN}💡 运行 /knowledge-wiki wiki 可自动生成/更新上述页面。${RESET}"
echo ""

# 退出码 1 表示"有待同步文档"，供 pre-push hook 判断
exit 1
