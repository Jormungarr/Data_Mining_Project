#!/usr/bin/env python3
"""
02_validate.py - integrity, consistency and plausibility checks on data/processed/.

Checks fall into four categories:
    A. Structure      row count, unique key, panel balance, column count
    B. Time           week boundary, within-season continuity, season labels
    C. Consistency    cross-source reconciliation (hospital sums vs HA Overall)
    D. Distribution   value ranges, missing rates, structural constants

Any failure returns exit code 1, so this can be used in CI.

Usage:
    python pipeline/02_validate.py
    python pipeline/02_validate.py --out-dir data/processed --report out/validation_report.txt
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent

OUTCOME_COLS = ["ae_first_attend", "ae_to_med_ip", "med_bed_occ_rate", "ped_bed_occ_rate"]
FLU_COLS = ["ILI_PMP", "ILI_AED", "Adm_65", "Adm_All", "Severe65", "flu_H1", "flu_H3", "flu_B", "flu_AandB"]
CAPACITY_COLS = ["beds_acute", "beds_infirmary", "beds_mental", "beds_mh", "ae_annual"]

EXPECTED_ROWS = 2448
EXPECTED_HOSPITALS = 17
EXPECTED_WEEKS = 144
EXPECTED_COLS = 34

# Plausible ranges. These are deliberately loose: they catch clear errors only
# and are never used to trim the data.
RANGE_CHECKS = {
    "ae_first_attend": (50, 800),
    "ae_to_med_ip": (0, 300),
    "med_bed_occ_rate": (40, 160),
    "ped_bed_occ_rate": (0, 160),
    "ILI_PMP": (0, 200),
    "Adm_65": (0, 20),
    "temp_mean": (0, 40),
    "temp_max": (0, 45),
    "temp_min": (-5, 35),
    "lat": (22.0, 22.6),
    "lon": (113.8, 114.5),
}

# Documented missing patterns: hospital -> {column: expected minimum missing rate (%)}
EXPECTED_MISSING = {
    "North Lantau Hospital": {"ae_to_med_ip": 99.0, "med_bed_occ_rate": 99.0, "ped_bed_occ_rate": 99.0},
}


class Report:
    """Collects check results, then prints and writes them at the end."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def section(self, title: str) -> None:
        self.lines.append("")
        self.lines.append("=" * 78)
        self.lines.append(title)
        self.lines.append("=" * 78)

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {label}"
        if detail:
            line += f"  —  {detail}"
        self.lines.append(line)
        if not ok:
            self.failures.append(f"{label}  {detail}")
        return ok

    def warn(self, label: str, detail: str = "") -> None:
        self.lines.append(f"  [WARN] {label}" + (f"  —  {detail}" if detail else ""))
        self.warnings.append(f"{label}  {detail}")

    def note(self, text: str) -> None:
        self.lines.append(f"         {text}")

    def render(self) -> str:
        self.lines.append("")
        self.lines.append("=" * 78)
        if self.failures:
            self.lines.append(f"Result: {len(self.failures)} check(s) FAILED")
            for f in self.failures:
                self.lines.append(f"  ✗ {f}")
        else:
            self.lines.append("Result: all checks passed")
        if self.warnings:
            self.lines.append(f"{len(self.warnings)} warning(s):")
            for w in self.warnings:
                self.lines.append(f"  ! {w}")
        self.lines.append("=" * 78)
        return "\n".join(self.lines)


def check_structure(r: Report, panel: pd.DataFrame, hk: pd.DataFrame) -> None:
    r.section("A. Structure")
    r.check(len(panel) == EXPECTED_ROWS, "Row count = 2,448", f"actual {len(panel):,}")
    r.check(
        panel.hospital.nunique() == EXPECTED_HOSPITALS,
        "Hospital count = 17",
        f"actual {panel.hospital.nunique()}",
    )
    r.check(
        panel.week_end.nunique() == EXPECTED_WEEKS,
        "Week count = 144",
        f"actual {panel.week_end.nunique()}",
    )
    r.check(
        len(panel) == panel.hospital.nunique() * panel.week_end.nunique(),
        "Panel is perfectly balanced (no missing rows)",
        f"{panel.hospital.nunique()} × {panel.week_end.nunique()} = {len(panel):,}",
    )
    dup = panel.duplicated(subset=["hospital", "week_end"]).sum()
    r.check(dup == 0, "Primary key (hospital, week_end) is unique", f"{dup} duplicates")
    r.check(panel.columns.duplicated().sum() == 0, "No duplicated column names")
    if len(panel.columns) != EXPECTED_COLS:
        r.warn("Column count differs from expected", f"expected {EXPECTED_COLS}, actual {len(panel.columns)}")
    else:
        r.check(True, f"Column count = {EXPECTED_COLS}", f"actual {len(panel.columns)}")
    r.check(len(hk) == EXPECTED_WEEKS, "Territory-wide weekly series = 144 rows", f"actual {len(hk)}")


def check_time(r: Report, panel: pd.DataFrame) -> None:
    r.section("B. Time axis")
    # Week boundary: week_end - week_start must be exactly 6 days
    span = (pd.to_datetime(panel.week_end) - pd.to_datetime(panel.week_start)).dt.days
    r.check(bool((span == 6).all()), "Each week spans exactly 7 days", f"span values {sorted(span.unique())}")

    # Season assignment, July boundary
    we = pd.to_datetime(panel.week_end)
    expected_season = np.where(
        we.dt.month < 7,
        (we.dt.year - 1).astype(str) + "-" + we.dt.year.astype(str).str[2:],
        we.dt.year.astype(str) + "-" + (we.dt.year + 1).astype(str).str[2:],
    )
    mismatch = int((expected_season != panel.season.values).sum())
    r.check(mismatch == 0, "Season labels match the July boundary", f"{mismatch} mismatches")

    # Within-season continuity: the HA does not publish every week of every
    # winter, so continuity is not required. What IS required is that any gap is
    # correctly flagged by prev_gap_days, or lags crossing it would be wrong.
    r.note("Within-season continuity (HA gaps must be flagged by prev_gap_days):")
    gap_rows = 0
    for season, grp in panel.groupby("season"):
        weeks = pd.Series(sorted(pd.to_datetime(grp.week_end.unique())))
        diffs = weeks.diff().dt.days.dropna()
        gaps = diffs[diffs != 7]
        n_gap_weeks = int((grp["prev_gap_days"] > 7).sum() // panel.hospital.nunique())
        gap_rows += n_gap_weeks
        r.note(
            f"    {season}: {len(weeks):>2} weeks  {weeks.iloc[0].date()} -> {weeks.iloc[-1].date()}"
            + (f"   {len(gaps)} gap(s) of {sorted(set(gaps.astype(int)))} days, {n_gap_weeks} week(s) affected"
               if len(gaps) else "   continuous")
        )
    r.check(gap_rows > 0, "Gaps are detected", f"{gap_rows} weeks follow a gap (prev_gap_days > 7)")

    # Definition check for prev_gap_days: it must equal the true interval, and 0
    # may only occur on the first week of a season
    per_week = panel.drop_duplicates(["season", "week_end"])[["season", "week_end", "week_in_season", "prev_gap_days"]].copy()
    per_week["week_end"] = pd.to_datetime(per_week.week_end)
    per_week = per_week.sort_values(["season", "week_end"])
    true_gap = per_week.groupby("season")["week_end"].diff().dt.days.fillna(0).astype(int)
    r.check(bool((true_gap.values == per_week["prev_gap_days"].values).all()),
            "prev_gap_days matches the true week interval everywhere",
            f"{int((true_gap.values != per_week['prev_gap_days'].values).sum())} mismatch(es)")

    # week_in_season must run 1, 2, 3, ... within each season
    ok_wi = True
    for season, grp in per_week.groupby("season"):
        if list(grp.week_in_season) != list(range(1, len(grp) + 1)):
            ok_wi = False
    r.check(ok_wi, "week_in_season runs consecutively from 1 in every season")

def check_consistency(r: Report, panel: pd.DataFrame, hk: pd.DataFrame, out_dir: pathlib.Path) -> None:
    r.section("C. Cross-source consistency")
    # Hospital sums should be close to HA Overall. The two are not identical by
    # construction, so this is an order-of-magnitude check only.
    per_week_sum = panel.groupby("week_end")["ae_first_attend"].sum().rename("sum_hospitals")
    merged = hk.set_index("week_end")["ae_first_attend"].rename("ha_overall").to_frame().join(per_week_sum)
    merged["ratio"] = merged.sum_hospitals / merged.ha_overall
    lo, hi = merged.ratio.min(), merged.ratio.max()
    r.check(
        0.70 <= lo and hi <= 1.30,
        "Sum of hospital A&E attendances is the same order as HA Overall",
        f"ratio range {lo:.3f} - {hi:.3f} (should be near 1)",
    )

    # Capacity covariates must be fully populated
    for col in CAPACITY_COLS:
        pct = panel[col].isna().mean() * 100
        r.check(pct == 0.0, f"Capacity covariate {col} has no missing values", f"missing {pct:.2f}%")

    # Coordinate coverage
    r.check(panel["lat"].isna().sum() == 0, "All hospitals have coordinates", f"{int(panel['lat'].isna().sum())} missing")

    # Temperature coverage
    r.check(panel["temp_mean"].isna().sum() == 0, "All weeks have a temperature record",
            f"{int(panel['temp_mean'].isna().sum())} missing")
    r.check(bool((panel["temp_days"] == 7).all()), "Every week has all 7 days of temperature",
            f"values {sorted(panel['temp_days'].unique())}")

    # Independent recount straight from the raw HA file
    raw_surge = out_dir.parent / "raw" / "ha" / "service_demand_surge_daily.json"
    if raw_surge.exists():
        import json
        recs = json.loads(raw_surge.read_text(encoding="utf-8"))
        daily = pd.DataFrame(recs)
        r.check(len(daily) == 16704, "Raw HA surge file has 16,704 rows", f"actual {len(daily):,}")
        n_days_overall = daily[daily.cluster == "HA Overall"]["date"].nunique()
        r.check(n_days_overall == 928, "HA Overall covers 928 distinct dates", f"actual {n_days_overall}")
    else:
        r.warn("Raw HA file not found, skipping the independent recount", str(raw_surge))


def check_distribution(r: Report, panel: pd.DataFrame) -> None:
    r.section("D. Values and missingness")

    r.note("Range checks (loose bounds, catching clear errors only):")
    for col, (lo, hi) in RANGE_CHECKS.items():
        if col not in panel.columns:
            continue
        s = pd.to_numeric(panel[col], errors="coerce").dropna()
        out_of_range = int(((s < lo) | (s > hi)).sum())
        ok = out_of_range == 0
        r.check(ok, f"{col} within [{lo}, {hi}]", f"{out_of_range} outside, actual range [{s.min():.2f}, {s.max():.2f}]")

    r.note("")
    r.note("Missing rate by variable:")
    for col in OUTCOME_COLS + FLU_COLS + CAPACITY_COLS:
        pct = panel[col].isna().mean() * 100
        r.note(f"    {col:20s} {pct:6.2f}%")

    r.note("")
    r.note("Structural fact: influenza predictors take one value per week across all 17 hospitals (no cross-sectional variation)")
    for col in FLU_COLS:
        nunique = panel.groupby("week_end")[col].nunique()
        ok = bool((nunique == 1).all())
        r.check(ok, f"{col} has exactly 1 value per week", f"{int((nunique != 1).sum())} anomalous weeks")

    r.note("")
    r.note("Confirmation of documented missing patterns:")
    for hospital, expectations in EXPECTED_MISSING.items():
        sub = panel[panel.hospital == hospital]
        if sub.empty:
            r.warn(f"Hospital expected to have missing data is absent from the panel: {hospital}")
            continue
        for col, min_pct in expectations.items():
            actual = sub[col].isna().mean() * 100
            r.check(actual >= min_pct, f"{hospital} / {col} still heavily missing", f"actual {actual:.1f}% (expected >= {min_pct}%)")

    r.note("")
    r.note("Paediatric occupancy coverage (only hospitals with a paediatric ward have values):")
    ped = panel.groupby("hospital")["ped_bed_occ_rate"].apply(lambda s: s.notna().mean() * 100).round(1)
    n_ped = int((ped > 50).sum())
    n_none = int((ped < 5).sum())
    n_partial = 17 - n_ped - n_none
    r.note(f"    {n_ped} hospitals complete, {n_none} with no data, {n_partial} partial")
    r.note("    Complete: " + ", ".join(f"{h.split()[0]}({p:.0f}%)" for h, p in ped.items() if p > 50))
    r.note("    None:     " + ", ".join(f"{h.split()[0]}" for h, p in ped.items() if p < 5))
    if n_partial:
        r.note("    Partial:  " + ", ".join(f"{h.split()[0]}({p:.0f}%)" for h, p in ped.items() if 5 <= p <= 50))
    r.check(n_ped + n_none + n_partial == 17, "Paediatric coverage fully accounted for (17 hospitals)",
            f"{n_ped} + {n_none} + {n_partial} = 17")
    r.check(n_ped >= 10, "Paediatric subsample is large enough to model (>= 10 hospitals)", f"actual {n_ped}")

    r.note("")
    r.note("Summary statistics:")
    desc = panel[OUTCOME_COLS + FLU_COLS + ["temp_mean", "beds_acute", "ae_annual"]].describe().T
    for name, row in desc.iterrows():
        r.note(f"    {name:20s} n={int(row['count']):>5d}  mean={row['mean']:>10.2f}  sd={row['std']:>9.2f}  "
               f"min={row['min']:>8.2f}  max={row['max']:>8.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "data" / "processed"))
    ap.add_argument("--report", default=str(ROOT / "out" / "validation_report.txt"))
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    panel_path = out_dir / "panel_hospital_week.csv"
    hk_path = out_dir / "hk_weekly.csv"
    if not panel_path.exists():
        raise SystemExit(f"Cannot find {panel_path}\nRun this first: python pipeline/01_build.py")

    panel = pd.read_csv(panel_path)
    hk = pd.read_csv(hk_path)

    r = Report()
    r.lines.append("=" * 78)
    r.lines.append("02_validate.py - analysis panel validation report")
    r.lines.append("=" * 78)
    r.lines.append(f"  Main table      {panel_path}   {panel.shape[0]:,} rows x {panel.shape[1]} cols")
    r.lines.append(f"  Weekly series   {hk_path}   {hk.shape[0]:,} rows x {hk.shape[1]} cols")

    check_structure(r, panel, hk)
    check_time(r, panel)
    check_consistency(r, panel, hk, out_dir)
    check_distribution(r, panel)

    text = r.render()
    print(text)

    report_path = pathlib.Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    print(f"\nReport written to {report_path}")

    return 1 if r.failures else 0


if __name__ == "__main__":
    sys.exit(main())
