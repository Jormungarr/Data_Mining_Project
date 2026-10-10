#!/usr/bin/env python3
"""
01_build.py - clean, aggregate and merge the raw files in data/raw/ into the analysis panel.

The raw data must already be in data/raw/ (sources and download links: data/raw/SOURCES.md).
This script does no network access; it only processes local files.

Outputs (data/processed/):
    panel_hospital_week.csv    Main analysis table: 17 hospitals x 144 weeks = 2,448 rows x 34 cols
    hk_weekly.csv              Territory-wide weekly series (HA Overall): 144 rows
    hospital_beds_annual.csv   Bed counts by hospital and financial year
    ae_attendances_annual.csv  Annual A&E attendances by hospital and financial year
    hospital_directory.csv     Hospital directory: cluster, A&E flag, coordinates
    data_dictionary.csv        Per-column variable dictionary

Steps:
    S0  Verify data/raw/ against the SHA256 values in _manifest.json
    S1  Read and parse the six source files
    S2  Harmonise hospital and cluster names across sources
    S3  Aggregate HA daily data into weeks on the Flu Express boundary (Sun-Sat)
    S4  Attach hospital capacity covariates, aligned on financial year
    S5  Aggregate HKO daily temperature onto the same week boundary
    S6  Merge into the main table, order columns, write all outputs

Conventions:
    * The week definition follows Flu Express From/To; To is the last day of the
      week (a Saturday). Every other source is aligned to that same boundary so
      that values are comparable across sources.
    * All aggregation is deterministic; there is no randomness anywhere.
    * Before building, files are compared against the SHA256 values in
      data/raw/_manifest.json and any missing or altered ones are reported.
      This is advisory only - you may have downloaded a newer official release.

Usage:
    python pipeline/01_build.py
    python pipeline/01_build.py --raw-dir data/raw --out-dir data/processed
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Constants: all processing rules live here so they are easy to review and change.
# --------------------------------------------------------------------------

# Response variables (HA Key Statistics during Service Demand Surge)
OUTCOME_COLS = [
    "ae_first_attend",   # A&E first attendances per day
    "ae_to_med_ip",      # Admissions to medical wards via A&E per day
    "med_bed_occ_rate",  # Medical bed occupancy %
    "ped_bed_occ_rate",  # Paediatric bed occupancy %
]

# Influenza predictors: source column name -> output column name
FLU_COLS = {
    "ILI_PMP": "ILI_PMP",                          # ILI rate, sentinel GOPC (primary predictor)
    "ILI_AED": "ILI_AED",                          # ILI rate, A&E departments
    "Adm_65_higher": "Adm_65",                     # Influenza admission rate, aged 65+
    "Adm_All": "Adm_All",                          # Influenza admission rate, all ages
    "SevereCase_65_higher": "Severe65",            # Severe influenza cases, aged 65+
    "H1": "flu_H1",                                # Laboratory-confirmed influenza A(H1)
    "H3": "flu_H3",                                # Laboratory-confirmed influenza A(H3)
    "B": "flu_B",                                  # Laboratory-confirmed influenza B
    "AandB": "flu_AandB",                          # Laboratory-confirmed influenza A + B
}

# Hospital name harmonisation across sources.
# Different HA divisions name the same hospital differently. Without an explicit
# mapping the merge drops rows silently (NaN rather than an error).
HOSPITAL_NAME_MAP = {
    "Ruttonjee & Tang Shiu Kin Hospitals": "Ruttonjee Hospital",
}

# The facility list merges Hong Kong Island into one cluster while the surge
# statistics split it into East and West, so the list is used only for coordinates.
CLUSTER_NAME_MAP = {
    "Hong Kong Island Cluster": "Hong Kong East/West",
}

# Bed specialty -> output column name
BED_SPECIALTY_MAP = {
    "General (Acute and Convalescent)": "beds_acute",
    "Infirmary": "beds_infirmary",
    "Mentally Ill": "beds_mental",
    "Mentally Handicapped": "beds_mh",
}

HKO_DATA_TYPES = {"CLMTEMP": "temp_mean", "CLMMAXT": "temp_max", "CLMMINT": "temp_min"}
HKO_YEARS = list(range(2019, 2027))


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def fiscal_year(date_like) -> str:
    """Date -> Hong Kong financial year string (starts 1 April), e.g. 2023-11-01 -> '2023-24'."""
    ts = pd.Timestamp(date_like)
    y = ts.year if ts.month >= 4 else ts.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def season_label(week_end: pd.Timestamp) -> str:
    """Week-ending date -> influenza season label (July boundary), e.g. 2020-01-04 -> '2019-20'."""
    y = week_end.year - 1 if week_end.month < 7 else week_end.year
    return f"{y}-{str(y + 1)[2:]}"


def require(path: pathlib.Path) -> pathlib.Path:
    if not path.exists():
        raise SystemExit(
            f"Missing raw file: {path}\n"
            f"Download it as described in data/raw/SOURCES.md and place it at that path."
        )
    return path


def verify_raw(raw: pathlib.Path) -> None:
    """Compare files against the SHA256 values in _manifest.json. Advisory only."""
    manifest = raw / "_manifest.json"
    if not manifest.exists():
        print("    (no _manifest.json found, skipping the integrity check)")
        return
    import hashlib

    recorded = json.loads(manifest.read_text(encoding="utf-8")).get("files", {})
    missing, changed, ok = [], [], 0
    for relpath, meta in recorded.items():
        path = raw / relpath
        if not path.exists():
            missing.append(relpath)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest == meta["sha256"]:
            ok += 1
        else:
            changed.append(relpath)
    print(f"    Match manifest: {ok}/{len(recorded)}")
    if missing:
        print(f"    ! missing {len(missing)}: {missing[:5]}{' ...' if len(missing) > 5 else ''}")
    if changed:
        print(f"    ! SHA256 mismatch {len(changed)}: {changed[:5]}{' ...' if len(changed) > 5 else ''}")
        print("      (the official data may have been updated, or the file was modified)")


# --------------------------------------------------------------------------
# S1 + S2  Read and harmonise names
# --------------------------------------------------------------------------
def load_flu(raw: pathlib.Path) -> pd.DataFrame:
    """Flu Express: weekly, and the reference time axis for this study."""
    df = pd.read_csv(require(raw / "flu/flux_data.csv"))
    df["week_end"] = pd.to_datetime(df["To"], format="%d/%m/%Y", errors="coerce")
    n_bad = int(df["week_end"].isna().sum())
    df = df.dropna(subset=["week_end"]).copy()
    df["week_start"] = df["week_end"] - pd.Timedelta(days=6)
    df["season"] = df["week_end"].map(season_label)
    df = df.sort_values("week_end").reset_index(drop=True)

    keep = ["week_start", "week_end", "season", "Year", "Week", "From", "To"] + list(FLU_COLS)
    df = df[keep].rename(columns=FLU_COLS)
    df = df.rename(columns={"Year": "flu_year", "Week": "flu_week"})
    df.attrs["n_unparsable_dates"] = n_bad
    return df


def load_surge(raw: pathlib.Path) -> pd.DataFrame:
    """HA Key Statistics during Service Demand Surge: daily x hospital."""
    records = json.loads(require(raw / "ha/service_demand_surge_daily.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    # Territory-wide summary rows have an empty hospital field. Name them
    # explicitly so they are never confused with a real hospital.
    df["hospital"] = df["hospital"].replace("", "HA Overall")
    df["hospital"] = df["hospital"].replace(HOSPITAL_NAME_MAP)
    return df.sort_values(["date", "cluster", "hospital"]).reset_index(drop=True)


def load_beds(raw: pathlib.Path) -> pd.DataFrame:
    """HA bed counts: financial year x cluster x hospital x specialty (long format)."""
    records = json.loads(require(raw / "ha/hospital_beds.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df = df[df["Specialty"] != "Overall"]           # drop the specialty total row
    df["hospital"] = df["Hospital"].replace(HOSPITAL_NAME_MAP)

    wide = (
        df.pivot_table(
            index=["Financial Year", "Cluster", "hospital"],
            columns="Specialty",
            values="Hospital Beds",
            aggfunc="sum",
        )
        .reset_index()
        .rename(columns={"Financial Year": "fy", "Cluster": "bed_cluster"})
    )
    wide = wide.rename(columns=BED_SPECIALTY_MAP)
    for col in BED_SPECIALTY_MAP.values():
        if col not in wide.columns:
            wide[col] = 0.0
    wide = wide[["fy", "bed_cluster", "hospital"] + list(BED_SPECIALTY_MAP.values())]

    # Some hospitals were renamed around 2017-18, so after mapping there can be
    # two rows for one hospital. Sum them.
    wide = wide.groupby(["fy", "hospital"], as_index=False).sum(numeric_only=True)
    wide["bed_cluster"] = wide["hospital"].map(
        df.drop_duplicates("hospital").set_index("hospital")["Cluster"]
    )
    return wide.sort_values(["hospital", "fy"]).reset_index(drop=True)


def load_ae_annual(raw: pathlib.Path) -> pd.DataFrame:
    """HA annual A&E attendances: financial year x hospital."""
    records = json.loads(require(raw / "ha/ae_attendances_annual.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df = df[~df["Hospital"].str.startswith("Overall")]   # drop cluster total rows
    df = df.rename(
        columns={
            "Financial Year": "fy",
            "Cluster": "ae_cluster",
            "Hospital": "hospital",
            "AE Attendances": "ae_annual",
        }
    )
    df["hospital"] = df["hospital"].replace(HOSPITAL_NAME_MAP)
    return (
        df[["fy", "hospital", "ae_annual"]]
        .groupby(["fy", "hospital"], as_index=False)["ae_annual"].sum()
        .sort_values(["hospital", "fy"])
        .reset_index(drop=True)
    )


def load_directory(raw: pathlib.Path) -> pd.DataFrame:
    """HA facility list: cluster, A&E flag, address, coordinates."""
    records = json.loads(require(raw / "ha/facility_hospitals.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df = df.rename(
        columns={
            "cluster_eng": "facility_cluster",
            "institution_eng": "hospital",
            "with_AE_service_eng": "with_AE",
            "address_eng": "address",
            "latitude": "lat",
            "longitude": "lon",
        }
    )
    df["hospital"] = df["hospital"].replace(HOSPITAL_NAME_MAP)
    df["facility_cluster"] = df["facility_cluster"].replace(CLUSTER_NAME_MAP)
    cols = ["hospital", "facility_cluster", "with_AE", "address", "lat", "lon"]
    return df[cols].drop_duplicates("hospital").sort_values("hospital").reset_index(drop=True)


def load_hko(raw: pathlib.Path) -> pd.DataFrame:
    """HKO daily temperature, merged into (date, temp_mean, temp_max, temp_min)."""
    frames = []
    for code, name in HKO_DATA_TYPES.items():
        parts = []
        for year in HKO_YEARS:
            path = raw / f"hko/{code}_{year}.csv"
            if not path.exists():
                raise SystemExit(f"Missing raw file: {path}\nDownload it as described in data/raw/SOURCES.md.")
            rows = []
            for line in path.read_text(encoding="utf-8-sig").splitlines()[2:]:  # first two lines are the title
                fields = [c.strip().strip('"') for c in line.split(",")]
                if len(fields) >= 4 and fields[0].isdigit():
                    value = fields[3]
                    rows.append(
                        {
                            "year": int(fields[0]),
                            "month": int(fields[1]),
                            "day": int(fields[2]),
                            name: float(value) if value not in ("", "N.A.", "***", "Trace") else None,
                        }
                    )
            parts.append(pd.DataFrame(rows))
        table = pd.concat(parts, ignore_index=True)
        table["date"] = pd.to_datetime(
            dict(year=table.year, month=table.month, day=table.day), errors="coerce"
        )
        frames.append(table.dropna(subset=["date"]).set_index("date")[[name]])

    hko = pd.concat(frames, axis=1).sort_index()
    return hko[~hko.index.duplicated(keep="first")]


# --------------------------------------------------------------------------
# S3  Daily -> weekly, aligned to the Flu Express week boundary
# --------------------------------------------------------------------------
def aggregate_to_weeks(daily: pd.DataFrame, flu: pd.DataFrame) -> pd.DataFrame:
    """Aggregate HA daily data into (cluster, hospital, week) means on the Flu Express boundary."""
    rows = []
    for r in flu.itertuples(index=False):
        window = daily[(daily["date"] >= r.week_start) & (daily["date"] <= r.week_end)]
        if window.empty:
            continue
        grouped = (
            window.groupby(["cluster", "hospital"])
            .agg(days=("date", "nunique"), **{c: (c, "mean") for c in OUTCOME_COLS})
            .reset_index()
        )
        grouped["week_start"] = r.week_start
        grouped["week_end"] = r.week_end
        grouped["season"] = r.season
        for col in FLU_COLS.values():
            grouped[col] = getattr(r, col)
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True)


def aggregate_hko_to_weeks(hko: pd.DataFrame, flu: pd.DataFrame) -> pd.DataFrame:
    """Aggregate temperature into weekly means on the same boundary."""
    rows = []
    for r in flu.itertuples(index=False):
        window = hko.loc[(hko.index >= r.week_start) & (hko.index <= r.week_end)]
        rec = {"week_end": r.week_end, "temp_days": len(window)}
        for name in HKO_DATA_TYPES.values():
            rec[name] = window[name].mean() if len(window) else float("nan")
        rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# S4-S6  Assemble the main table
# --------------------------------------------------------------------------
def build(raw: pathlib.Path, out: pathlib.Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)

    print("S0  Verify data/raw/ integrity")
    verify_raw(raw)

    print("\nS1  Read raw files")
    flu = load_flu(raw)
    surge = load_surge(raw)
    beds = load_beds(raw)
    ae_annual = load_ae_annual(raw)
    directory = load_directory(raw)
    hko = load_hko(raw)
    print(f"    Flu Express        {len(flu):>6,} weeks  {flu.week_end.min().date()} -> {flu.week_end.max().date()}")
    print(f"    HA surge stats     {len(surge):>6,} rows   {surge.date.min().date()} -> {surge.date.max().date()}")
    print(f"    HA bed counts      {len(beds):>6,} rows   FY {beds.fy.min()} -> {beds.fy.max()}")
    print(f"    HA annual A&E      {len(ae_annual):>6,} rows")
    print(f"    HA facility list   {len(directory):>6,} institutions")
    print(f"    HKO temperature    {len(hko):>6,} days   {hko.index.min().date()} -> {hko.index.max().date()}")

    print("\nS2  Harmonise hospital and cluster names")
    surge_hospitals = sorted(set(surge.loc[surge.hospital != "HA Overall", "hospital"]))
    matched = sorted(set(surge_hospitals) & set(beds["hospital"]))
    unmatched = sorted(set(surge_hospitals) - set(beds["hospital"]))
    print(f"    Hospitals in surge data   {len(surge_hospitals)}")
    print(f"    Matched to bed table      {len(matched)}/{len(surge_hospitals)}"
          + (f"   unmatched: {unmatched}" if unmatched else ""))
    print(f"    Name mapping              {HOSPITAL_NAME_MAP}")

    print("\nS3  HA daily -> weekly")
    weekly = aggregate_to_weeks(surge, flu)
    hospital_week = weekly[weekly.hospital != "HA Overall"].copy()
    hk_week = weekly[weekly.hospital == "HA Overall"].drop(columns=["cluster", "hospital"])
    print(f"    Hospital x week           {hospital_week.shape}")
    print(f"    Territory-wide weekly     {hk_week.shape}")

    print("\nS4  Hospital capacity covariates")
    hospital_week["fy"] = hospital_week["week_end"].map(fiscal_year)
    panel = hospital_week.merge(beds.drop(columns=["bed_cluster"]), on=["fy", "hospital"], how="left")
    panel = panel.merge(ae_annual, on=["fy", "hospital"], how="left")
    panel = panel.merge(
        directory[["hospital", "with_AE", "lat", "lon"]], on="hospital", how="left"
    )
    print(f"    After merge               {panel.shape}")

    print("\nS5  Temperature -> weekly")
    hko_week = aggregate_hko_to_weeks(hko, flu)
    print(f"    Weekly temperature        {hko_week.shape}")

    print("\nS6  Assemble main table")
    panel = panel.merge(hko_week, on="week_end", how="left")
    hk_week = hk_week.merge(hko_week, on="week_end", how="left")

    # Column order: identifiers -> response -> predictors -> covariates -> flags
    order = (
        ["hospital", "cluster", "fy", "season", "week_start", "week_end"]
        + OUTCOME_COLS
        + list(FLU_COLS.values())
        + ["beds_acute", "beds_infirmary", "beds_mental", "beds_mh", "ae_annual", "with_AE", "lat", "lon"]
        + ["temp_mean", "temp_max", "temp_min", "temp_days", "days"]
        + ["week_in_season", "prev_gap_days"]
    )

    # Beds and annual A&E are published only up to FY2024-25. Later weeks carry
    # the last published year forward - bed counts are slow-moving.
    for col in ["beds_acute", "beds_infirmary", "beds_mental", "beds_mh", "ae_annual"]:
        panel[col] = panel.groupby("hospital")[col].ffill()

    # Within-season week index, plus days since the previous published week.
    # The HA does not publish every week of every winter (gaps appear from
    # 2023-24 onward), so a naive shift(1) can reach back several weeks.
    # prev_gap_days > 7 means the previous row is not really 'last week',
    # and lags crossing such a gap must be masked when modelling.
    week_order = (
        panel[["season", "week_end"]]
        .drop_duplicates()
        .sort_values(["season", "week_end"])
        .reset_index(drop=True)
    )
    week_order["week_in_season"] = week_order.groupby("season").cumcount() + 1
    week_order["prev_gap_days"] = (
        week_order.groupby("season")["week_end"]
        .transform(lambda s: pd.to_datetime(s).diff().dt.days)
    )
    week_order["prev_gap_days"] = week_order["prev_gap_days"].fillna(0).astype(int)

    panel["week_end"] = pd.to_datetime(panel["week_end"])
    panel = panel.merge(
        week_order[["season", "week_end", "week_in_season", "prev_gap_days"]],
        on=["season", "week_end"],
        how="left",
    )
    hk_week["week_end"] = pd.to_datetime(hk_week["week_end"])
    hk_week = hk_week.merge(
        week_order[["season", "week_end", "week_in_season", "prev_gap_days"]],
        on=["season", "week_end"],
        how="left",
    )

    panel = panel[order].sort_values(["week_end", "hospital"]).reset_index(drop=True)
    print(f"    Final main table          {panel.shape}")
    n_gap = int((panel["prev_gap_days"] > 7).sum())
    print(f"    Weeks after a gap         {n_gap} rows (prev_gap_days > 7, "
          f"longest {int(panel['prev_gap_days'].max())} days)")

    # -- Write out -------------------------------------------------------------
    panel.to_csv(out / "panel_hospital_week.csv", index=False)
    hk_week.to_csv(out / "hk_weekly.csv", index=False)
    beds.to_csv(out / "hospital_beds_annual.csv", index=False)
    ae_annual.to_csv(out / "ae_attendances_annual.csv", index=False)
    directory.to_csv(out / "hospital_directory.csv", index=False)
    write_data_dictionary(panel, hk_week, out / "data_dictionary.csv")

    print("\nOutputs:")
    for name in [
        "panel_hospital_week.csv",
        "hk_weekly.csv",
        "hospital_beds_annual.csv",
        "ae_attendances_annual.csv",
        "hospital_directory.csv",
        "data_dictionary.csv",
    ]:
        path = out / name
        print(f"    {name:32s} {path.stat().st_size:>10,} bytes")

    return {"panel": panel, "hk_week": hk_week}


# --------------------------------------------------------------------------
# Variable dictionary
# --------------------------------------------------------------------------
DATA_DICTIONARY = [
    ("hospital", "Identifier", "Hospital name, harmonised across sources", "Categorical", "17 values"),
    ("cluster", "Identifier", "Hospital cluster", "Categorical", "7 values"),
    ("fy", "Identifier", "Financial year (starts 1 April)", "Categorical", "2019-20 ... 2026-27"),
    ("season", "Identifier", "Influenza season label (July boundary)", "Categorical", "8 seasons"),
    ("week_start", "Identifier", "First day of the week (Sunday)", "Date", "2019-11-25 ..."),
    ("week_end", "Identifier", "Last day of the week (Saturday), aligned to Flu Express To", "Date", "2019-12-07 ... 2026-08-08"),
    ("ae_first_attend", "Response", "A&E first attendances (weekly daily mean)", "Count", "attendances/day"),
    ("ae_to_med_ip", "Response", "Admissions to medical wards via A&E (weekly daily mean)", "Count", "admissions/day"),
    ("med_bed_occ_rate", "Response", "Medical bed occupancy (weekly daily mean)", "Bounded proportion", "%"),
    ("ped_bed_occ_rate", "Response", "Paediatric bed occupancy (weekly daily mean)", "Bounded proportion", "%"),
    ("ILI_PMP", "Predictor", "ILI rate, sentinel general outpatient clinics [primary predictor]", "Continuous", "per 1,000 consultations"),
    ("ILI_AED", "Predictor", "ILI rate, A&E departments", "Continuous", "per 1,000 consultations"),
    ("Adm_65", "Predictor", "Influenza admission rate, aged 65+", "Continuous", "per 1,000 population"),
    ("Adm_All", "Predictor", "Influenza admission rate, all ages", "Continuous", "per 1,000 population"),
    ("Severe65", "Predictor", "Severe influenza cases, aged 65+", "Count", "cases/week"),
    ("flu_H1", "Predictor", "Laboratory-confirmed influenza A(H1)", "Count", "cases/week"),
    ("flu_H3", "Predictor", "Laboratory-confirmed influenza A(H3)", "Count", "cases/week"),
    ("flu_B", "Predictor", "Laboratory-confirmed influenza B", "Count", "cases/week"),
    ("flu_AandB", "Predictor", "Laboratory-confirmed influenza A + B", "Count", "cases/week"),
    ("beds_acute", "Covariate", "Acute and convalescent beds (annual)", "Continuous", "beds"),
    ("beds_infirmary", "Covariate", "Infirmary beds (annual)", "Continuous", "beds"),
    ("beds_mental", "Covariate", "Mentally ill beds (annual)", "Continuous", "beds"),
    ("beds_mh", "Covariate", "Mentally handicapped beds (annual)", "Continuous", "beds"),
    ("ae_annual", "Covariate", "Total A&E attendances in that financial year", "Continuous", "attendances/year"),
    ("with_AE", "Covariate", "Whether the institution runs an A&E service", "Categorical", "Yes"),
    ("lat", "Covariate", "Hospital latitude", "Continuous", "decimal degrees"),
    ("lon", "Covariate", "Hospital longitude", "Continuous", "decimal degrees"),
    ("temp_mean", "Covariate", "HKO daily mean temperature (weekly mean)", "Continuous", "deg C"),
    ("temp_max", "Covariate", "HKO daily maximum temperature (weekly mean)", "Continuous", "deg C"),
    ("temp_min", "Covariate", "HKO daily minimum temperature (weekly mean)", "Continuous", "deg C"),
    ("temp_days", "Data quality", "Days with a temperature reading in the week", "Count", "0-7"),
    ("days", "Data quality", "Days of HA data actually published for the week", "Count", "1-7"),
    ("week_in_season", "Data quality", "Index of the week within its season", "Count", "1..N"),
    ("prev_gap_days", "Data quality",
     "Days since the previous published week in the same season. 7 means truly "
     "adjacent; >7 means an HA publication gap, and lags crossing it must be masked",
     "Count", "0 (first week of season) / 7 / >7"),
]


def write_data_dictionary(panel: pd.DataFrame, hk_week: pd.DataFrame, path: pathlib.Path) -> None:
    rows = []
    for name, role, desc, dtype, unit in DATA_DICTIONARY:
        if name in panel.columns:
            col = panel[name]
            rows.append(
                {
                    "column": name,
                    "table": "panel_hospital_week",
                    "role": role,
                    "description": desc,
                    "dtype": dtype,
                    "unit": unit,
                    "n_non_null": int(col.notna().sum()),
                    "n_missing": int(col.isna().sum()),
                    "pct_missing": round(float(col.isna().mean() * 100), 2),
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"), help="directory holding the raw data")
    ap.add_argument("--out-dir", default=str(ROOT / "data" / "processed"), help="output directory")
    ap.add_argument("--check-raw-only", action="store_true",
                    help="only verify data/raw/, do not build")
    args = ap.parse_args()

    raw_dir = pathlib.Path(args.raw_dir)
    if args.check_raw_only:
        print("=" * 78)
        print("data/raw/ integrity check")
        print("=" * 78)
        verify_raw(raw_dir)
        return 0

    print("=" * 78)
    print("01_build.py - building the analysis panel")
    print("=" * 78)
    build(raw_dir, pathlib.Path(args.out_dir))
    print("\nDone. Next: python pipeline/02_validate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
