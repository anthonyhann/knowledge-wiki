#!/usr/bin/env bash
# knowledge-wiki prepare-commit-msg hook
# 在 commit 时分析 staged 文件的代码变更，判断是否需要生成/更新知识文档
# 非阻断式提示，用户可选择跳过
# 安装：cp references/scripts/prepare-commit-msg.sh .git/hooks/prepare-commit-msg && chmod +x .git/hooks/prepare-commit-msg

set -uo pipefail

# ─── 环境变量跳过 ───
# KB_SKIP_DOCS=1 跳过本 hook
# CI=true / NONINTERACTIVE=1 跳过本 hook
if [ "${KB_SKIP_DOCS:-0}" = "1" ] || [ "${CI:-}" = "true" ] || [ "${NONINTERACTIVE:-0}" = "1" ]; then
  exit 0
fi

KB_DIR=".knowledge"

# 仅在有 .knowledge/ 目录时执行
if [ ! -d "$KB_DIR" ]; then
  exit 0
fi

# 检查是否为交互式终端（非 TTY 时跳过）
if [ ! -t 0 ]; then
  exit 0
fi

# ─── 获取 staged 文件 ───
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)

if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

# ─── 过滤：排除 .knowledge/ 自身、纯测试文件、非代码文件 ───
CODE_EXTENSIONS="go|php|ts|tsx|js|jsx|py|java|rs|rb|vue|proto|api|sql"
EXCLUDE_PATTERNS="^\.knowledge/|_test\.|\.test\.|\.spec\.|test_|/tests?/|/mock/|/mocks/"

STAGED_CODE_FILES=$(echo "$STAGED_FILES" | grep -E "\.($CODE_EXTENSIONS)$" | grep -vE "$EXCLUDE_PATTERNS" || true)

if [ -z "$STAGED_CODE_FILES" ]; then
  # 无有效代码文件变更，静默退出
  exit 0
fi

# ─── 计算变更规模 ───
ADDED_LINES=$(git diff --cached --numstat -- $STAGED_CODE_FILES 2>/dev/null | awk '{sum += $1} END {print sum+0}')
NEW_FILES=$(git diff --cached --name-only --diff-filter=A -- $STAGED_CODE_FILES 2>/dev/null | wc -l | tr -d ' ')
MODIFIED_FILES=$(echo "$STAGED_CODE_FILES" | wc -l | tr -d ' ')

# ─── 阈值判断：有效代码行 < 20 且无新增文件时静默跳过 ───
if [ "${ADDED_LINES:-0}" -lt 20 ] && [ "${NEW_FILES:-0}" -eq 0 ]; then
  exit 0
fi

# ─── 快速检测：是否有明显的知识点变更 ───
# 检测新增接口/路由/handler/migration/model/配置等
HAS_KNOWLEDGE_SIGNAL=false

# 新增 API/路由文件
if echo "$STAGED_CODE_FILES" | grep -qE "(handler|controller|route|router|api|endpoint)"; then
  HAS_KNOWLEDGE_SIGNAL=true
fi

# 新增 migration/model/schema
if echo "$STAGED_CODE_FILES" | grep -qE "(migration|model|schema|entity|table)"; then
  HAS_KNOWLEDGE_SIGNAL=true
fi

# 新增 .proto/.api 定义文件
if echo "$STAGED_CODE_FILES" | grep -qE "\.(proto|api)$"; then
  HAS_KNOWLEDGE_SIGNAL=true
fi

# 新增配置/运维相关
if echo "$STAGED_CODE_FILES" | grep -qE "(config|conf|deploy|docker|k8s|helm)"; then
  HAS_KNOWLEDGE_SIGNAL=true
fi

# 大量代码变更（>= 100 行新增）也触发
if [ "${ADDED_LINES:-0}" -ge 100 ]; then
  HAS_KNOWLEDGE_SIGNAL=true
fi

if [ "$HAS_KNOWLEDGE_SIGNAL" = false ]; then
  exit 0
fi

# ─── 输出知识文档建议 ───
echo ""
echo "📖 [knowledge-wiki] 检测到可能需要文档化的代码变更"
echo "─────────────────────────────────────────────────"
echo "   变更文件: ${MODIFIED_FILES} 个代码文件（+${ADDED_LINES} 行）"
echo "   新增文件: ${NEW_FILES} 个"
echo ""
echo "   涉及文件（前 5 个）:"
echo "$STAGED_CODE_FILES" | head -5 | sed 's/^/     • /'
if [ "$MODIFIED_FILES" -gt 5 ]; then
  echo "     ...（共 ${MODIFIED_FILES} 个）"
fi
echo ""
echo "─────────────────────────────────────────────────"
echo "   commit 完成后，可运行以下命令分析并生成知识文档："
echo ""
echo "     /knowledge-wiki docs"
echo ""
echo "   或在 AI 编程助手 中直接使用："
echo "     /knowledge-wiki docs --last"
echo ""
echo "─────────────────────────────────────────────────"
echo ""

# 不阻断 commit，仅提示
exit 0
