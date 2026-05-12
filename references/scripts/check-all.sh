#!/usr/bin/env bash
# check-all.sh — 文档规范检查（frontmatter、断链、行数超限）
# 用法：bash processes/scripts/check-all.sh [目录]
# CI 质量门禁：EXIT_CODE=1 表示有 ERROR 级别问题

set -euo pipefail

TARGET="${1:-.knowledge}"
ERRORS=0; WARNINGS=0
RED="\033[31m"; YELLOW="\033[33m"; GREEN="\033[32m"; RESET="\033[0m"

# 跳过 generated/ 和 .kb-meta/
find "$TARGET" -name "*.md" \
  -not -path "*/generated/*" \
  -not -path "*/.kb-meta/*" \
  -not -path "*/archives/*" | while IFS= read -r f; do

  # 检查 frontmatter
  if ! head -1 "$f" | grep -q "^---"; then
    echo -e "${RED}[ERROR]${RESET} 缺少 frontmatter：$f"
    ERRORS=$((ERRORS+1))
  fi

  # 检查行数
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 800 ]; then
    echo -e "${RED}[ERROR]${RESET} 文件超过 800 行（${lines}行）：$f"
    ERRORS=$((ERRORS+1))
  fi

  # 检查 WikiLink 断链
  grep -o '\[\[[^]]*\]\]' "$f" 2>/dev/null | while read -r link; do
    target=$(echo "$link" | sed 's/\[\[//;s/\]\]//;s/|.*//')
    target_file=$(find "$TARGET/pages" "$TARGET/docs" -name "${target}.md" 2>/dev/null | head -1)
    if [ -z "$target_file" ]; then
      echo -e "${YELLOW}[WARNING]${RESET} 断链 ${link} in $f"
      WARNINGS=$((WARNINGS+1))
    fi
  done
done

echo ""
echo -e "检查完成：${RED}ERROR ${ERRORS}${RESET} | ${YELLOW}WARNING ${WARNINGS}${RESET}"
[ "$ERRORS" -gt 0 ] && exit 1 || exit 0
