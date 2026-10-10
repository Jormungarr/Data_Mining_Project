#!/usr/bin/env bash
#
# run_all.sh — 一键复现整条数据管道。
#
#   ./pipeline/run_all.sh              增量：已有的原始文件跳过下载
#   ./pipeline/run_all.sh --fresh      彻底重来：删除 data/raw 与 data/processed 后重建
#   ./pipeline/run_all.sh --check-only  只校验本地数据，不联网
#
# 依赖：uv（用于创建/同步虚拟环境）。首次运行会自动安装依赖。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# uv 的缓存目录默认写到 ~/.cache/uv；在受限环境（沙箱）里可能不可写，故显式指定。
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_ROOT/.uv-cache}"

FRESH=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --fresh)      FRESH=1 ;;
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)    sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
log "0/4  准备虚拟环境"
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
  log "1/1  离线校验原始文件"
  "$PY" pipeline/01_download.py --check
  log "完成"
  exit 0
fi

if [ "$FRESH" -eq 1 ]; then
  log "清理旧数据"
  rm -rf data/raw data/processed
  mkdir -p data/raw data/processed
  echo "已删除 data/raw 与 data/processed"
fi

log "1/4  下载原始数据"
"$PY" pipeline/01_download.py

log "2/4  校验原始文件完整性（SHA256）"
"$PY" pipeline/01_download.py --check

log "3/4  构建分析面板"
"$PY" pipeline/02_build.py

log "4/4  验证分析面板"
"$PY" pipeline/03_validate.py

log "全部完成"
cat <<'EOF'

产出文件：
  data/processed/panel_hospital_week.csv     主分析表（17 医院 × 144 周）
  data/processed/hk_weekly.csv               全港周序列
  data/processed/hospital_beds_annual.csv    医院年度病床数
  data/processed/ae_attendances_annual.csv   医院年度急症室服务量
  data/processed/hospital_directory.csv      医院名录与坐标
  data/processed/data_dictionary.csv         变量字典
  out/validation_report.txt                  验证报告

原始文件与 SHA256 清单：
  data/raw/                                  原始文件（只下载不改写）
  data/raw/_manifest.json                    每个文件的 URL / 字节数 / SHA256 / 抓取时间
  data/raw/_provenance.json                  data.gov.hk 数据集官方元数据
EOF
