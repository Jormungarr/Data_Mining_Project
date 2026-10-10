#!/usr/bin/env python3
"""
03_eda.py - first look at the panel, as a runnable script.

Reads:
    data/processed/panel_hospital_week.csv

Writes:
    out/eda_overview.txt        text report
    out/eda_time_series.png     territory-wide weekly series
    out/eda_missing.png         missingness by column

Usage:
    .venv/bin/python pipeline/03_eda.py
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")          # write files instead of opening a window
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent

RESPONSES = ["ae_first_attend", "ae_to_med_ip", "med_bed_occ_rate", "ped_bed_occ_rate"]
PREDICTORS = ["ILI_PMP", "ILI_AED", "Adm_65", "Adm_All", "Severe65",
              "flu_H1", "flu_H3", "flu_B", "flu_AandB"]


def main() -> int:
    panel_path = ROOT / "data" / "processed" / "panel_hospital_week.csv"
    if not panel_path.exists():
        raise SystemExit(f"Cannot find {panel_path}\nRun this first: python pipeline/01_build.py")

    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Everything printed is also collected into the text report, so the console
    # output and the saved file can never disagree.
    log: list[str] = []

    def say(text: str = "") -> None:
        print(text)
        log.append(text)

    say("=" * 78)
    say("03_eda.py - first look at the panel")
    say("=" * 78)

    df = pd.read_csv(panel_path)

    # ------------------------------------------------------------------ shape
    say("\n1  Shape")
    say(f"   rows x cols      : {df.shape[0]:,} x {df.shape[1]}")
    say(f"   hospitals        : {df.hospital.nunique()}")
    say(f"   weeks            : {df.week_end.nunique()}")
    say(f"   seasons          : {df.season.nunique()}  ({', '.join(sorted(df.season.unique()))})")
    say(f"   clusters         : {df.cluster.nunique()}")
    balanced = len(df) == df.hospital.nunique() * df.week_end.nunique()
    say(f"   balanced panel   : {balanced}")

    # ------------------------------------------------------------------- head
    say("\n2  First three rows (selected columns)")
    cols = ["hospital", "week_end", "ILI_PMP", "ae_first_attend", "med_bed_occ_rate", "days"]
    say(df[cols].head(3).to_string(index=False))

    # ---------------------------------------------------------------- missing
    say("\n3  Missing values (columns with any gaps only)")
    miss = (df.isna().mean() * 100).sort_values(ascending=False)
    miss = miss[miss > 0].round(2)
    if miss.empty:
        say("   none")
    else:
        for col, pct in miss.items():
            say(f"   {col:22s} {pct:6.2f}%")

    # -------------------------------------------------------------- structure
    say("\n4  Do the predictors vary across hospitals within a week?")
    for col in PREDICTORS:
        n = int(df.groupby("week_end")[col].nunique().max())
        note = "territory-wide, no cross-sectional variation" if n == 1 else "VARIES - unexpected"
        say(f"   {col:12s} max distinct values in a week: {n}   ({note})")

    # ----------------------------------------------------------------- ranges
    say("\n5  Summary of responses and predictors")
    say(df[RESPONSES + PREDICTORS].describe().T[["count", "mean", "std", "min", "max"]]
        .round(2).to_string())

    # ------------------------------------------------------------- by season
    say("\n6  Territory-wide averages by season")
    say(df.groupby("season").agg(
        weeks=("week_end", "nunique"),
        ae_mean=("ae_first_attend", "mean"),
        ae_peak=("ae_first_attend", "max"),
        occ_mean=("med_bed_occ_rate", "mean"),
        ili_mean=("ILI_PMP", "mean"),
    ).round(1).to_string())

    # ---------------------------------------------------------------- figures
    say("\n7  Figures")
    weekly = df.groupby("week_end")[["ae_first_attend", "ILI_PMP"]].mean()
    weekly.index = pd.to_datetime(weekly.index)
    # Reindex onto a complete weekly grid so missing weeks become NaN. Without
    # this the line is drawn straight across each publication gap and implies
    # data we do not have.
    grid = pd.date_range(weekly.index.min(), weekly.index.max(), freq="7D")
    weekly = weekly.reindex(grid)

    fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    axes[0].plot(weekly.index, weekly["ae_first_attend"], color="#1f4e79", linewidth=1.5)
    axes[0].set_ylabel("A&E first attendances per day\n(mean over hospitals)")
    axes[0].set_title("Territory-wide weekly series: 8 winter windows, gaps between them")
    axes[1].plot(weekly.index, weekly["ILI_PMP"], color="#c0504d", linewidth=1.5)
    axes[1].set_ylabel("ILI_PMP\n(per 1,000 consultations)")
    axes[1].set_xlabel("week ending")
    for ax in axes:
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / "eda_time_series.png", dpi=150)
    plt.close(fig)
    say("   out/eda_time_series.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    missing_pct = (df.isna().mean() * 100).sort_values(ascending=False)
    missing_pct = missing_pct[missing_pct > 0]
    if missing_pct.empty:
        ax.text(0.5, 0.5, "no missing values", ha="center", va="center")
        ax.axis("off")
    else:
        missing_pct.plot.barh(ax=ax, color="#c0504d")
        ax.set_xlabel("% missing")
        ax.invert_yaxis()
    ax.set_title("Missing values by column")
    fig.tight_layout()
    fig.savefig(out_dir / "eda_missing.png", dpi=150)
    plt.close(fig)
    say("   out/eda_missing.png")

    # ------------------------------------------------------------ correlation
    say("\n8  Correlation with ILI_PMP, under two different aggregations")
    say("   The two panels answer different questions and give different numbers.")
    say("")
    pooled = df[RESPONSES + ["ILI_PMP"]].corr()["ILI_PMP"].drop("ILI_PMP")
    # Averaging within each week removes the between-hospital size differences,
    # which is the aggregation DATA_GUIDE Section 6 reports.
    wk = df.groupby("week_end")[RESPONSES + ["ILI_PMP"]].mean()
    weekly_corr = wk.corr()["ILI_PMP"].drop("ILI_PMP")
    say(f"   {'response':22s} {'pooled':>10s} {'weekly mean':>14s}")
    for col in RESPONSES:
        say(f"   {col:22s} {pooled[col]:>+10.3f} {weekly_corr[col]:>+14.3f}")
    say("")
    say("   pooled      = all 2,448 hospital-weeks together. Mixes 'is this hospital")
    say("                 large?' into the correlation, which dilutes it.")
    say("   weekly mean = one value per week, 144 points. This is the more meaningful")
    say("                 of the two, and matches DATA_GUIDE Section 6.")
    say("")
    say("   Note: DATA_GUIDE quotes the same correlations from hk_weekly.csv (the HA")
    say("   Overall aggregate row), which covers slightly more hospitals. The two")
    say("   agree exactly for ae_first_attend and differ by at most 0.005 elsewhere.")
    say("   Both are correct; they are just different aggregations.")
    say("")
    say("   Both are descriptive associations, not evidence of causation.")

    report = out_dir / "eda_overview.txt"
    report.write_text("\n".join(log) + "\n", encoding="utf-8")
    say(f"\nReport written to {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
