#!/usr/bin/env bash
#
# run_all.sh — 一键构建并验证分析数据集。
#
#   ./pipeline/run_all.sh               构建 + 验证
#   ./pipeline/run_all.sh --check-only   只检查 data/raw/ 完整性，不做构建
#
# 前提：原始数据已在 data/raw/ 下。来源与下载链接见 data/raw/SOURCES.md。
# 依赖：uv（用于创建/同步虚拟环境）。首次运行会自动安装依赖。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# uv 的缓存目录默认写到 ~/.cache/uv；在受限环境（沙箱）里可能不可写，故显式指定。
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_ROOT/.uv-cache}"

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)    sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
log "0/2  准备虚拟环境"
if ! command -v uv >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV="$HOME/.local/bin/uv"
  else
    echo "找不到 uv。请先安装：curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
  fi
else
  UV="uv"
fi
if [ ! -d .venv ]; then
  "$UV" venv --python 3.12
fi
"$UV" sync --quiet
PY=".venv/bin/python"
echo "Python: $($PY --version)"

if [ "$CHECK_ONLY" -eq 1 ]; then
  log "1/1  检查 data/raw/ 完整性"
  "$PY" pipeline/01_build.py --check-raw-only
  log "完成"
  exit 0
fi

log "1/2  构建分析面板"
"$PY" pipeline/01_build.py

log "2/2  验证分析面板"
"$PY" pipeline/02_validate.py

log "完成"
cat <<'EOF'

产出文件：
  data/processed/panel_hospital_week.csv     主分析表（17 医院 × 144 周）
  data/processed/hk_weekly.csv               全港周序列
  data/processed/hospital_beds_annual.csv    医院年度病床数
  data/processed/ae_attendances_annual.csv   医院年度急症室服务量
  data/processed/hospital_directory.csv      医院名录与坐标
  data/processed/data_dictionary.csv         变量字典
  out/validation_report.txt                  验证报告

数据结构、变量含义与探索空间 → DATA_GUIDE.md
原始数据来源与下载链接       → data/raw/SOURCES.md
EOF
