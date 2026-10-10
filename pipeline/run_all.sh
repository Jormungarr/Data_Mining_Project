#!/usr/bin/env bash
#
# run_all.sh - build and validate the analysis dataset in one command.
#
#   ./pipeline/run_all.sh               build + validate
#   ./pipeline/run_all.sh --check-only   only verify data/raw/, do not build
#
# Requires the raw data to be present in data/raw/.
# Sources and download links: data/raw/SOURCES.md
# Requires uv (creates and syncs the virtual environment).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# uv writes its cache to ~/.cache/uv by default. That may not be writable in a
# restricted environment, so point it somewhere inside the project.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_ROOT/.uv-cache}"

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)    sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
log "0/2  Preparing the virtual environment"
if ! command -v uv >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV="$HOME/.local/bin/uv"
  else
    echo "uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
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
  log "1/1  Verifying data/raw/ integrity"
  "$PY" pipeline/01_build.py --check-raw-only
  log "Done"
  exit 0
fi

log "1/2  Building the analysis panel"
"$PY" pipeline/01_build.py

log "2/2  Validating the analysis panel"
"$PY" pipeline/02_validate.py

log "Done"
cat <<'EOF'

Outputs:
  data/processed/panel_hospital_week.csv     Main analysis table (17 hospitals x 144 weeks)
  data/processed/hk_weekly.csv               Territory-wide weekly series
  data/processed/hospital_beds_annual.csv    Annual bed counts by hospital
  data/processed/ae_attendances_annual.csv   Annual A&E attendances by hospital
  data/processed/hospital_directory.csv      Hospital directory and coordinates
  data/processed/data_dictionary.csv         Variable dictionary
  out/validation_report.txt                  Validation report

Data structure, variables and what is analysable  ->  DATA_GUIDE.md
Raw data sources and download links              ->  data/raw/SOURCES.md

This script covers the data steps only. Analysis and modelling scripts are
yours to write: read from data/processed/, write to out/, and run them with
  .venv/bin/python pipeline/<your_script>.py
See README "Running your own script" for the conventions.
EOF
