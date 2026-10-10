# Emergency Care Load During Influenza Seasons in Hong Kong

A weekly panel dataset of emergency-care service load across Hong Kong public
hospitals, together with the reproducible pipeline that builds it.

**Research question:** how does rising influenza activity translate into
emergency-care demand at Hong Kong public hospitals, and does that transmission
differ systematically across hospitals?

| | |
|---|---|
| Main analysis table | `data/processed/panel_hospital_week.csv` |
| Size | **2,448 rows × 34 columns** (17 hospitals × 144 weeks, balanced panel) |
| Period | 2019-12-07 → 2026-08-08 (8 influenza seasons) |
| Sources | Department of Health, Hospital Authority, Hong Kong Observatory (29 public data files) |
| Variable dictionary | [`data/processed/data_dictionary.csv`](data/processed/data_dictionary.csv) |
| **Data structure guide** | **[`DATA_GUIDE.md`](DATA_GUIDE.md)** — read this first · [中文版](DATA_GUIDE.zh.md) |

---

## Where to start

Four common situations. Pick the row that matches you.

| If you want to... | Read |
|---|---|
| **Just use the data** | The table above, then `data/processed/`. You do not need to run anything. |
| **Understand what the columns mean** | [`DATA_GUIDE.md`](DATA_GUIDE.md) Sections 0–3. Section 0 walks through a single row. |
| **Analyse the data** | Read [Section 4](DATA_GUIDE.md#4-three-structural-facts-you-must-know) **first** — it explains the constraints that will otherwise trip you up — then [Section 7](DATA_GUIDE.md#7-what-you-can-and-cannot-do) for what is and is not answerable. |
| **Rebuild the dataset** | The setup below, then [Pipeline details](#pipeline-details). |
| **Run a model** | [Running your own script](#running-your-own-script) below. |

Unfamiliar with terms like *panel data*, *fixed effects* or *negative binomial*?
There is a plain-language [glossary](DATA_GUIDE.md#10-glossary) at the end of the
Data Guide.

---

## Getting started

**Just want the data?** `data/processed/` already holds the finished tables.

**Want to rebuild it yourself?**

```bash
./pipeline/run_all.sh          # build then validate, about 10 seconds
```

The first run creates `.venv` and installs dependencies via `uv` (Python 3.12).
**No network access is required** — the raw data ships with the repository in
`data/raw/`.

```bash
./pipeline/run_all.sh                # build + validate
./pipeline/run_all.sh --check-only    # just verify data/raw/ integrity
```

The pipeline reads `data/raw/` directly and downloads nothing. To refresh to the
latest official data, download the files listed in
[`data/raw/SOURCES.md`](data/raw/SOURCES.md) and overwrite the existing ones.

The pipeline is **deterministic**: re-running it on the same raw data produces
byte-identical CSV output.

---

## Repository layout

```
.
├── README.md                     This file: setup and pipeline
├── DATA_GUIDE.md                 Data structure, variables, what is analysable (English)
├── DATA_GUIDE.zh.md              Same guide in Chinese
├── LICENSE                       MIT, plus data attribution
│
├── pipeline/                     The whole reproducible pipeline
│   ├── run_all.sh                One-command driver
│   ├── 01_build.py               Clean, aggregate, merge -> analysis tables
│   └── 02_validate.py            Structural / temporal / consistency / distribution checks
│
├── data/
│   ├── raw/                      Raw files, byte-for-byte, never rewritten
│   │   ├── SOURCES.md            Download links and checksums
│   │   ├── _manifest.json        URL / size / SHA256 / retrieval time per file
│   │   ├── _provenance.json      Official metadata from data.gov.hk
│   │   └── flu/  ha/  hko/
│   └── processed/                Output tables (regenerable)
│
├── out/
│   └── validation_report.txt     Validation report (40+ assertions)
│
└── pyproject.toml / uv.lock      Pinned dependencies
```

**`data/raw/` is never rewritten.** All cleaning happens in `01_build.py`, so the
result can always be traced back to the source files and the exact version used.

---

## Data sources

| # | Provider | Dataset | Frequency | Role |
|---|---|---|---|---|
| 1 | Department of Health, CHP | [Flu Express figures](https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express) | Weekly | Predictors |
| 2 | Hospital Authority | [Key Statistics during Service Demand Surge](https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge) | Daily | Response variables |
| 3 | Hospital Authority | [Inpatient and Day Inpatient Services Throughput](https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ipdp) | Financial year | Covariate |
| 4 | Hospital Authority | [Ambulatory and Community Services Throughput](https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ambulatory-community) | Financial year | Covariate |
| 5 | Hospital Authority | [Hospital / institution list](https://data.gov.hk/sc-data/dataset/hospital-hadata-health-care-facilities) | Quarterly | Geography |
| 6 | Hong Kong Observatory | [Open Data API](https://data.weather.gov.hk/weatherAPI/doc/HKO_Open_Data_API_Documentation.pdf) `CLMTEMP` / `CLMMAXT` / `CLMMINT` | Daily | Covariate |

Download links and SHA256 checksums are recorded in
[`data/raw/SOURCES.md`](data/raw/SOURCES.md) and `data/raw/_manifest.json`.
Official dataset metadata from data.gov.hk is archived in
`data/raw/_provenance.json`.

---

## Pipeline details

### 01_build.py

Runs as seven labelled steps:

| Step | What it does |
|---|---|
| **S0** | Compares files against the SHA256 values in `_manifest.json` and reports any missing or altered ones (advisory only, never fatal) |
| **S1** | Reads and parses the six sources |
| **S2** | Harmonises hospital and cluster names across sources (`HOSPITAL_NAME_MAP`) |
| **S3** | Aggregates HA daily data into weeks on the Flu Express boundary (Sunday–Saturday) |
| **S4** | Attaches hospital capacity covariates, aligned on financial year |
| **S5** | Aggregates HKO daily temperature onto the same week boundary |
| **S6** | Merges, orders columns, forward-fills bed counts, adds data-quality flags, writes out |

The processing conventions are collected in a constants block at the top of the
file: the week definition follows Flu Express `From`/`To`; hospital name mappings;
annual forward-fill for bed counts and A&E attendances.

**Traps encountered while building the table** — worth reading if you merge from
`data/raw/` yourself — are documented in
[Section 5 of the Data Guide](DATA_GUIDE.md#5-traps-already-handled-in-the-pipeline).

### 02_validate.py

Four categories of checks, 40+ assertions in total. Any failure returns exit
code 1, so it can be used in CI.

| Category | Contents |
|---|---|
| **A. Structure** | Row count 2,448; 17 hospitals; 144 weeks; panel balance; unique key; column count |
| **B. Time** | Each week spans exactly 7 days; season labels; gaps correctly flagged; within-season week index contiguous |
| **C. Consistency** | Hospital sums vs HA Overall; covariates fully populated; independent recount of raw files |
| **D. Distribution** | Value ranges; missing rates; structural constancy of the influenza predictors; known missing patterns |

The latest report is at [`out/validation_report.txt`](out/validation_report.txt).

### Running your own script

The repository ships the data pipeline only. Analysis and modelling scripts are
yours to write, and are deliberately not versioned — `.gitignore` keeps
`pipeline/*.py` out of the repository except `01_build.py` and `02_validate.py`,
and keeps everything in `out/` out except the validation report.

Write your script, then run it with the project interpreter so it picks up the
installed packages:

```bash
.venv/bin/python pipeline/my_analysis.py
```

Conventions to follow:

| | |
|---|---|
| **Read from** | `data/processed/*.csv` — never modify `data/raw/` |
| **Write to** | `out/` |
| **Resolve paths** | `ROOT = pathlib.Path(__file__).resolve().parent.parent`, so the script works from any directory |
| **Print** | Use `print()`. A bare expression like `df.shape` echoes in the interactive interpreter but outputs nothing in a script |
| **Plots** | Start with `matplotlib.use("Agg")` and finish with `fig.savefig(...)`. Calling `.plot()` alone produces no file |
| **Lags** | Group by `season` and mask rows where `prev_gap_days > 7` — see [DATA_GUIDE 4.2](DATA_GUIDE.md#42-the-time-axis-is-discontinuous--eight-winter-windows) |
| **Standard errors** | Cluster by `week_end`, not by hospital — see [DATA_GUIDE 7.2](DATA_GUIDE.md#72-suggested-methods-and-robustness-checks) |
| **New packages** | `uv add <package>`, then commit the updated `pyproject.toml` and `uv.lock` |

`run_all.sh` covers the data steps only, which are deterministic and
reproducible. If you want one command for everything, append your script to the
end of it.

---

## Output tables

| File | Size | Contents |
|---|---|---|
| `panel_hospital_week.csv` | 2,448 × 34 | **Main analysis table** (hospital × week) |
| `hk_weekly.csv` | 144 × 23 | Territory-wide weekly series (HA Overall) |
| `hospital_beds_annual.csv` | hospital × FY | Bed counts, wide format (FY2008-09 onward) |
| `ae_attendances_annual.csv` | hospital × FY | Annual A&E attendances (FY2008-09 onward) |
| `hospital_directory.csv` | 44 institutions | Names, clusters, A&E flag, address, coordinates |
| `data_dictionary.csv` | 34 rows | Variable dictionary (type, unit, missing counts) |

Variable meanings, sample structure, what is analysable and what is not:
**→ [`DATA_GUIDE.md`](DATA_GUIDE.md)**

---

## Verifying reproducibility

```bash
# Fresh clone from GitHub, then run without network access
git clone <repo> && cd <repo> && ./pipeline/run_all.sh
# -> raw integrity 29/29
# -> S0-S6 complete
# -> all four check categories pass
# -> all six output files byte-identical to the upstream repository

# Check the raw data only
./pipeline/run_all.sh --check-only
# -> 29/29 match the manifest
```

---

## Environment

Dependencies are pinned in `pyproject.toml` and `uv.lock`:

```
Python 3.12
pandas 3.0.6    numpy 2.5.3    scipy 1.18.1    statsmodels 0.15.0
matplotlib 3.11.2    requests 2.34.2    lxml 6.1.3
```

Only `pandas` is needed to run the pipeline end to end, and no network access is
required. The remaining packages support downstream modelling.

In restricted environments (such as a sandbox) the default `uv` cache directory
may not be writable. Set:

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
```

`run_all.sh` already defaults to this location.
