#!/usr/bin/env bash
# knowledge-wiki 基础工具依赖检查脚本
# 由 /knowledge-wiki init Step 0 调用
#
# 退出码：
#   0 = 必需工具齐全（OPTIONAL 缺失不阻断）
#   1 = 必需工具缺失（执行安装命令后重试）
#   2 = 检查脚本自身错误
#
# 使用：bash references/scripts/check-deps.sh
#       bash references/scripts/check-deps.sh --install        # 一键安装缺失的必需工具
#       bash references/scripts/check-deps.sh --install-browser # 一键安装浏览器自动化生态可选工具

# 注：故意不开启 set -u，因为 macOS bash 3.2 在中文字符与 read 切分时偶发误判
# 通过显式数组初始化和参数默认值（${var:-}）保证安全

MODE="check"
case "${1:-}" in
  --install)         MODE="install" ;;
  --install-browser) MODE="install-browser" ;;
esac

OS="$(uname -s)"
case "$OS" in
  Darwin) OS_FAMILY="mac" ;;
  Linux)  OS_FAMILY="linux" ;;
  *)      OS_FAMILY="other" ;;
esac

# ─────────────────────────────────────────────────────────────────────────────
# Group A：核心工具（knowledge-wiki 主流程依赖）
# 格式：name|level|tagline|desc|mac_cmd|linux_cmd
# ─────────────────────────────────────────────────────────────────────────────
CORE_TOOLS=(
  "rg|REQUIRED|快速代码检索|关键词检索/追溯（ask、links、refs、deprecate）|brew install ripgrep|apt install -y ripgrep || yum install -y ripgrep"
  "git|REQUIRED|版本控制|hook 安装与 commit-msg 触发|brew install git|apt install -y git || yum install -y git"
  "jq|OPTIONAL|JSON 处理器|hook 脚本中解析 frontmatter（建议安装）|brew install jq|apt install -y jq || yum install -y jq"
)

# ─────────────────────────────────────────────────────────────────────────────
# Group B：浏览器/文档自动化生态（按场景互补，全部 OPTIONAL）
# ─────────────────────────────────────────────────────────────────────────────
BROWSER_TOOLS=(
  "agent-browser|OPTIONAL|AI工具调用的极速瑞士军刀|轻量·ref引用·50+命令；URL 抽取首选|npm i -g @aigc/agent-browser|npm i -g @aigc/agent-browser"
  "browser-harness|OPTIONAL|AI编程助手的自愈浏览器手|Claude Code·自愈·动态页面；选择器易变页面优选|npm i -g @aigc/browser-harness|npm i -g @aigc/browser-harness"
  "playwright|OPTIONAL|工程化测试的坚实基石|E2E测试·稳定·详细报告；流程固定的录入/扫描自动化|npm i -g playwright && npx playwright install chromium|npm i -g playwright && npx playwright install chromium"
  "browser-use|OPTIONAL|LLM 自主操作的完整大脑|Python·规划·Deep Research；多步骤自主决策录入|pipx install browser-use 2>/dev/null || pip3 install --user browser-use|pipx install browser-use 2>/dev/null || pip3 install --user browser-use"
  "page-agent|OPTIONAL|中文网页理解的领域专家|中文优化·多模态；中文网页站点优选|npm i -g page-agent|npm i -g page-agent"
)

# ─────────────────────────────────────────────────────────────────────────────
# 检查实现
# ─────────────────────────────────────────────────────────────────────────────
MISSING_REQ=()
MISSING_OPT_CORE=()
MISSING_OPT_BROWSER=()
INSTALL_CMDS_REQ=()
INSTALL_CMDS_BROWSER=()

# 命令检测：兼容 npm 全局包（部分包不在 PATH，通过 npm ls -g --depth=0 兜底）
detect() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1 && return 0
  # browser-use 在 python 包里
  if [[ "$name" == "browser-use" ]]; then
    python3 -c "import browser_use" 2>/dev/null && return 0
  fi
  # npm 全局包兜底
  if command -v npm >/dev/null 2>&1; then
    npm ls -g --depth=0 2>/dev/null | grep -q " ${name}@" && return 0
  fi
  return 1
}

# 选取当前 OS 的安装命令
pick_cmd() {
  local mac_cmd="$1" linux_cmd="$2"
  case "$OS_FAMILY" in
    mac)   echo "$mac_cmd" ;;
    linux) echo "$linux_cmd" ;;
    *)     echo "$mac_cmd" ;;
  esac
}

print_section() {
  printf "\n── %s ──\n" "$1"
  printf "%-18s %-10s %-32s %s\n" "工具" "状态" "定位关键词" "用途"
  printf "%-18s %-10s %-32s %s\n" "------" "----" "----------" "----"
}

check_group() {
  local arr_name="$1"
  local kind="$2"   # core | browser
  # bash 3.2 兼容：通过 eval 间接展开数组
  local entries=()
  eval "entries=( \"\${${arr_name}[@]}\" )"
  for entry in "${entries[@]}"; do
    IFS='|' read -r name level tagline desc mac_cmd linux_cmd <<< "$entry"
    if detect "$name"; then
      printf "%-18s %-10s %-32s %s\n" "$name" "✓ 已安装" "$tagline" "$desc"
    else
      if [[ "$level" == "REQUIRED" ]]; then
        printf "%-18s %-10s %-32s %s\n" "$name" "✗ 缺失" "$tagline" "$desc"
        MISSING_REQ+=("$name")
        INSTALL_CMDS_REQ+=("$(pick_cmd "$mac_cmd" "$linux_cmd")")
      else
        printf "%-18s %-10s %-32s %s [optional]\n" "$name" "○ 未装" "$tagline" "$desc"
        if [[ "$kind" == "browser" ]]; then
          MISSING_OPT_BROWSER+=("$name|$(pick_cmd "$mac_cmd" "$linux_cmd")")
          INSTALL_CMDS_BROWSER+=("$(pick_cmd "$mac_cmd" "$linux_cmd")")
        else
          MISSING_OPT_CORE+=("$name|$(pick_cmd "$mac_cmd" "$linux_cmd")")
        fi
      fi
    fi
  done
}

printf "\n[knowledge-wiki] 工具依赖检查（OS=%s）\n" "$OS_FAMILY"

print_section "Group A：核心工具（主流程必需/建议）"
check_group CORE_TOOLS core

print_section "Group B：浏览器自动化生态（URL 处理；任选其一即可）"
check_group BROWSER_TOOLS browser

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# 安装模式
# ─────────────────────────────────────────────────────────────────────────────
run_cmds() {
  local arr_name="$1"
  local cmds=()
  eval "cmds=( \"\${${arr_name}[@]}\" )"
  for cmd in "${cmds[@]}"; do
    echo "  $ $cmd"
    bash -c "$cmd" || echo "  ⚠️ 失败：$cmd（请手动执行）"
  done
}

if [[ "$MODE" == "install" ]]; then
  if [[ ${#INSTALL_CMDS_REQ[@]} -eq 0 ]]; then
    echo "[install] 必需工具已齐全，无需安装。"
    exit 0
  fi
  echo "[install] 安装缺失的必需工具："
  run_cmds INSTALL_CMDS_REQ
  echo ""
  echo "[install] 完成。重新检查："
  exec "$0"
fi

if [[ "$MODE" == "install-browser" ]]; then
  if [[ ${#INSTALL_CMDS_BROWSER[@]} -eq 0 ]]; then
    echo "[install-browser] 浏览器自动化工具已齐全，无需安装。"
    exit 0
  fi
  echo "[install-browser] 安装缺失的浏览器自动化工具："
  echo "（这会安装全部缺失的可选工具；若只需其中一项，请手动执行对应命令）"
  run_cmds INSTALL_CMDS_BROWSER
  echo ""
  echo "[install-browser] 完成。重新检查："
  exec "$0"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 输出结论
# ─────────────────────────────────────────────────────────────────────────────
if [[ ${#MISSING_REQ[@]} -gt 0 ]]; then
  echo "❌ 缺失必需工具：${MISSING_REQ[*]}"
  echo ""
  echo "一键安装："
  echo "  bash $0 --install"
  echo ""
  echo "或手动安装："
  for cmd in "${INSTALL_CMDS_REQ[@]}"; do
    echo "  $ $cmd"
  done
  exit 1
fi

# 浏览器工具：全部缺失才警告（任一存在即可处理 URL）
INSTALLED_BROWSER=$(( ${#BROWSER_TOOLS[@]} - ${#MISSING_OPT_BROWSER[@]} ))
if [[ $INSTALLED_BROWSER -eq 0 ]]; then
  echo "⚠️ 浏览器自动化生态全部未安装：将无法录入任何 URL（飞书/Apipost/公网）"
  echo ""
  echo "选型建议（任选其一即可）："
  echo "  agent-browser   → 轻量CLI，AI 调用首选"
  echo "  browser-harness → 自愈，适合动态/选择器易变页面"
  echo "  playwright      → 工程化，适合稳定流程"
  echo "  browser-use     → Python，多步骤 LLM 自主决策"
  echo "  page-agent      → 中文优化，阿里系站点"
  echo ""
  echo "一键安装全部："
  echo "  bash $0 --install-browser"
  echo ""
  echo "或单装一个（推荐 agent-browser 起步）："
  for entry in "${MISSING_OPT_BROWSER[@]}"; do
    IFS='|' read -r name cmd <<< "$entry"
    echo "  $ $cmd     # $name"
  done
elif [[ ${#MISSING_OPT_BROWSER[@]} -gt 0 ]]; then
  echo "ℹ️ 浏览器自动化生态部分安装（已装 $INSTALLED_BROWSER / ${#BROWSER_TOOLS[@]}），主流程可用。"
  echo "   未装：$(IFS=,; echo "${MISSING_OPT_BROWSER[*]%%|*}")"
fi

# 核心可选工具
if [[ ${#MISSING_OPT_CORE[@]} -gt 0 ]]; then
  echo ""
  for entry in "${MISSING_OPT_CORE[@]}"; do
    IFS='|' read -r name cmd <<< "$entry"
    echo "ℹ️ 核心可选工具未装：$name（$cmd）"
  done
fi

echo ""
echo "✓ 必需工具检查通过，可继续 init。"
exit 0

